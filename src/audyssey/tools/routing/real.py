import importlib.resources
import json
import time

import httpx2
from openai.types.chat import ChatCompletionMessageParam
from langsmith import tracing_context
from pydantic import TypeAdapter, ValidationError

from openai.types.chat import (
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionToolParam,
)

from audyssey.contracts import (
    AddSource,
    Clarify,
    Drop,
    Generate,
    Job,
    Keep,
    NoCommand,
    Render,
    Reseparate,
    RouteDecision,
    SetGain,
    SetPitch,
    parse_decision,
)
from audyssey.settings import LLMEndpoint
from audyssey.tools.planning.llm import chat_client
from audyssey.tools.routing import Routed, summarize

DECISION_SCHEMA = TypeAdapter(RouteDecision).json_schema()

RULES = """규칙:
- 요청 하나에는 명령 하나만 고릅니다.
- 대상 소스가 둘 이상 해당하면 clarify(ambiguous_target)를 씁니다.
- 오디오 편집이 아닌 요청(질문, 잡담, 자막, 영상 자르기, 배속, 화면 필터)은 none을 씁니다.
- source_id는 job.sources의 id 또는 "residual"만 씁니다.
- 출력은 JSON 하나이고 type 필드로 종류를 고릅니다."""

TOOLS_PROMPT = """당신은 영상 오디오 편집 요청을 명령 하나로 바꾸는 라우터입니다. 명령을 실행하지 않고 고르기만 합니다.
규칙:
- 도구를 정확히 하나만 호출합니다.
- source_id는 job.sources의 id 또는 "residual"만 씁니다.
- 오디오 편집이지만 대상이 모호하거나, 양이 없거나, 편집이 둘 이상이거나, 할 수 없는 요청이면 해당 reason으로 clarify를 호출합니다.
- 오디오 편집이 아닌 요청(질문, 잡담, 자막, 영상 자르기, 배속, 화면 필터)은 none을 호출합니다."""

MODELS = {
    "keep": Keep,
    "drop": Drop,
    "set_gain": SetGain,
    "set_pitch": SetPitch,
    "reseparate": Reseparate,
    "generate": Generate,
    "add_source": AddSource,
    "render": Render,
    "clarify": Clarify,
    "none": NoCommand,
}


def _commands() -> dict:
    raw = importlib.resources.files("audyssey.tools.routing").joinpath(
        "descriptions.json"
    )
    return json.loads(raw.read_text(encoding="utf-8"))["commands"]


def _inline(node, defs: dict):
    """Replace every $ref with its definition; some servers reject $ref."""
    if isinstance(node, dict):
        if "$ref" in node:
            return _inline(defs[node["$ref"].rsplit("/", 1)[-1]], defs)
        return {k: _inline(v, defs) for k, v in node.items() if k != "$defs"}
    if isinstance(node, list):
        return [_inline(v, defs) for v in node]
    return node


def _tools() -> list[ChatCompletionToolParam]:
    tools: list[ChatCompletionToolParam] = []
    for name, d in _commands().items():
        schema = MODELS[name].model_json_schema()
        schema["properties"].pop("type", None)
        if "required" in schema:
            schema["required"] = [r for r in schema["required"] if r != "type"]
        parameters = _inline(schema, schema.get("$defs", {}))
        parameters.pop("title", None)
        description = " ".join(
            [d["when"], d["instead"], d["params"], *(f"예: {e}" for e in d["examples"])]
        )
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            }
        )
    return tools


def _system_prompt() -> str:
    commands = _commands()
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
    reasoning_effort: str | None = None,
    fmt: str = "tools",
) -> Routed:
    use_tools = fmt == "tools"
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": TOOLS_PROMPT if use_tools else _system_prompt()},
        {
            "role": "user",
            "content": json.dumps(
                {"job": summarize(job), "request": request}, ensure_ascii=False
            ),
        },
    ]
    extra_body = {"reasoning_effort": reasoning_effort} if reasoning_effort else None
    start = time.perf_counter()
    # The request text is the user's; it never goes to LangSmith.
    with tracing_context(enabled=False):
        client = chat_client(endpoint, transport=transport)
        if use_tools:
            response = client.chat.completions.create(
                model=endpoint.model,
                messages=messages,
                temperature=0,
                tools=_tools(),
                tool_choice="required",
                extra_body=extra_body,
            )
        else:
            response = client.chat.completions.create(
                model=endpoint.model,
                messages=messages,
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "route_decision",
                        "schema": DECISION_SCHEMA,
                    },
                },
                extra_body=extra_body,
            )
    latency_ms = (time.perf_counter() - start) * 1000
    usage = response.usage
    decision, error = None, None
    try:
        if not response.choices:
            raise TypeError("model returned no content")
        message = response.choices[0].message
        if use_tools:
            calls = message.tool_calls or []
            if len(calls) != 1:
                raise TypeError(f"expected one tool call, got {len(calls)}")
            call = calls[0]
            if (
                not isinstance(call, ChatCompletionMessageFunctionToolCall)
                or call.function.name not in MODELS
            ):
                raise TypeError("model called an unknown tool")
            data = {
                "type": call.function.name,
                **json.loads(call.function.arguments or "{}"),
            }
        else:
            if not message.content:
                raise TypeError("model returned no content")
            data = json.loads(message.content)
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
