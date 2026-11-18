import importlib.resources
import json
import time

import httpx2
from openai.types.chat import ChatCompletionMessageParam
from langsmith import tracing_context
from pydantic import TypeAdapter, ValidationError

from audyssey.contracts import Job, RouteDecision, parse_decision
from audyssey.settings import LLMEndpoint
from audyssey.tools.planning.llm import chat_client
from audyssey.tools.routing import Routed, summarize

DECISION_SCHEMA = TypeAdapter(RouteDecision).json_schema()

RULES = """규칙:
- 요청 하나에는 명령 하나만 고릅니다.
- 대상 소스가 둘 이상 해당하면 clarify(ambiguous_target)를 씁니다.
- 지원하지 않는 요청은 none 또는 clarify(unsupported)를 씁니다.
- source_id는 job.sources의 id 또는 "residual"만 씁니다.
- 출력은 JSON 하나이고 type 필드로 종류를 고릅니다."""


def _system_prompt() -> str:
    raw = importlib.resources.files("audyssey.tools.routing").joinpath(
        "descriptions.json"
    )
    commands = json.loads(raw.read_text(encoding="utf-8"))["commands"]
    lines = [
        "당신은 영상 오디오 편집 요청을 명령 하나로 바꾸는 라우터입니다. 명령을 실행하지 않고 고르기만 합니다.",
        "",
    ]
    for name, d in commands.items():
        lines += [
            f"## {name}",
            f"언제: {d['when']}",
            f"다른 명령: {d['instead']}",
            f"값: {d['params']}",
            *(f"예: {e}" for e in d["examples"]),
            "",
        ]
    return "\n".join(lines) + RULES


def route(
    request: str,
    job: Job,
    endpoint: LLMEndpoint,
    transport: httpx2.BaseTransport | None = None,
) -> Routed:
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _system_prompt()},
        {
            "role": "user",
            "content": json.dumps(
                {"job": summarize(job), "request": request}, ensure_ascii=False
            ),
        },
    ]
    start = time.perf_counter()
    # The request text is the user's; it never goes to LangSmith.
    with tracing_context(enabled=False):
        response = chat_client(endpoint, transport=transport).chat.completions.create(
            model=endpoint.model,
            messages=messages,
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "route_decision", "schema": DECISION_SCHEMA},
            },
        )
    latency_ms = (time.perf_counter() - start) * 1000
    usage = response.usage
    decision, error = None, None
    try:
        if not response.choices or not response.choices[0].message.content:
            raise TypeError("model returned no content")
        data = json.loads(response.choices[0].message.content)
        if not isinstance(data, dict):
            raise TypeError("output is not a JSON object")
        decision = parse_decision(data)
    except json.JSONDecodeError:
        error = "model output is not valid JSON"
    except TypeError as e:
        error = str(e)
    except ValidationError as e:
        error = f"model output failed the schema ({e.error_count()} errors)"
    return Routed(
        decision,
        error,
        latency_ms,
        usage.prompt_tokens if usage else 0,
        usage.completion_tokens if usage else 0,
    )
