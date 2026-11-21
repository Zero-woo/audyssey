import json
import time

import httpx2
from langsmith import tracing_context
from openai.types.chat import ChatCompletionMessageParam

from audyssey.contracts import (
    Drop,
    Generate,
    Job,
    Keep,
    NoCommand,
    Render,
    Reseparate,
    parse_decision,
)
from audyssey.settings import LLMEndpoint
from audyssey.tools.planning.llm import chat_client
from audyssey.tools.routing import Routed, summarize
from audyssey.tools.routing.real import _commands, parse, tool

REASONS = {
    "ambiguous_target": '대상 소스가 둘 이상 해당하거나 "왼쪽"처럼 화면 위치로 가리켜 하나로 정할 수 없음',
    "missing_value": '크기나 음높이를 바꾸려는데 양이 없거나 "조금"처럼 모호함',
    "composite": "한 요청에 편집이 둘 이상 들어 있음",
    "unsupported": "대사 재생성, 무음 영상 재분리, 범위 밖 값처럼 실행할 수 없는 편집 요청",
    "other": "편집 의도는 있지만 위 경우가 아니면서 명령을 하나로 정할 수 없음",
}
QUESTIONS = {
    "ambiguous_target": "어느 소리를 말씀하시는 건가요?",
    "missing_value": "얼마나 바꿀까요?",
    "composite": "한 번에 하나씩 요청해 주시겠어요?",
    "unsupported": "그 편집은 지원하지 않습니다. 다른 방법으로 해 볼까요?",
    "other": "무엇을 바꿀지 다시 말씀해 주시겠어요?",
}
VALUE = {"set_gain", "set_pitch", "add_source"}
TARGETED = {"keep": Keep, "drop": Drop, "reseparate": Reseparate, "generate": Generate}

VALUE_PROMPT = """당신은 영상 오디오 편집 요청에서 명령의 값을 채우는 도구입니다.
명령과 대상 소스는 이미 정해졌습니다(decided). 요청(request)과 job의 현재 값을 보고 도구 하나를 호출해 값만 채웁니다."""
ESCAPE_PROMPT = "\n요청에 양이 없거나 모호하면 clarify를 호출합니다."


def _questions(job: Job) -> dict:
    commands = _commands()
    options = {
        name: f"{d['when']} {d['instead']}"
        for name, d in commands.items()
        if name not in ("clarify", "none")
    }
    options |= {f"clarify_{r}": f"되물어야 함: {t}" for r, t in REASONS.items()}
    options["none"] = f"{commands['none']['when']} {commands['none']['instead']}"
    targets = {
        s.id: f"{s.plan.name} ({s.plan.kind}, {'켜짐' if s.keep else '꺼짐'})"
        for s in job.sources
    } | {"residual": "residual: 분리되지 않고 남은 나머지 소리"}
    return {
        "decision": {
            "type": "choice",
            "instructions": "사용자 요청(request)을 처리할 편집 명령 하나를 고르세요.",
            "criteria": options,
        },
        "target": {
            "type": "choice",
            "instructions": "사용자 요청(request)이 가리키는 소스 하나를 고르세요.",
            "criteria": targets,
        },
        "residual_stem": {
            "type": "noul",
            "instructions": "요청이 residual stem(잔여 소리)도 따로 내보내라고 하나요?",
        },
    }


def _ask(url, request, job, transport) -> tuple[dict, dict, int]:
    body = {
        "model": "x",
        "state": {"job": summarize(job), "request": request},
        "questions": _questions(job),
    }
    with httpx2.Client(transport=transport, timeout=60) as client:
        response = client.post(f"{url.rstrip('/')}/v1/systemone", json=body)
    response.raise_for_status()
    out = response.json()
    answers = out["answers"]
    choice, target = answers["decision"]["choice"], answers["target"]["choice"]
    if not isinstance(choice, str) or not isinstance(target, str):
        raise TypeError("decision server answered a non-string choice")
    noul = float(answers["residual_stem"]["noul"])
    tokens = int(out.get("usage", {}).get("input_tokens", 0))
    return {"choice": choice, "target": target, "noul": noul}, answers, tokens


def _fill(request, job, endpoint, kind, target, escape, effort, transport):
    commands = _commands()
    fixed = None if kind == "add_source" else {"source_id": {"enum": [target]}}
    tools = [tool(kind, commands[kind], fixed)]
    if escape:
        reason = {"reason": {"enum": ["missing_value"]}}
        tools.append(tool("clarify", commands["clarify"], reason))
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": VALUE_PROMPT + (ESCAPE_PROMPT if escape else "")},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "job": summarize(job),
                    "request": request,
                    "decided": {"type": kind, "source_id": target},
                },
                ensure_ascii=False,
            ),
        },
    ]
    extra_body = {"reasoning_effort": effort} if effort else None
    # The request text is the user's; it never goes to LangSmith.
    with tracing_context(enabled=False):
        response = chat_client(endpoint, transport=transport).chat.completions.create(
            model=endpoint.model,
            messages=messages,
            temperature=0,
            tools=tools,
            tool_choice="required",
            extra_body=extra_body,
        )
    decision, error = parse(response, True)
    offered = {t["function"]["name"] for t in tools}
    if decision is not None and decision.type not in offered:
        decision, error = None, "model called a tool that was not offered"
    usage = response.usage
    return (
        decision,
        error,
        usage.prompt_tokens if usage else 0,
        (usage.completion_tokens if usage else 0),
    )


def route(
    request: str,
    job: Job,
    decision_url: str,
    endpoint: LLMEndpoint,
    escape: bool = False,
    reasoning_effort: str | None = None,
    decision_transport: httpx2.BaseTransport | None = None,
    llm_transport: httpx2.BaseTransport | None = None,
) -> Routed:
    start = time.perf_counter()
    try:
        answer, raw, tokens = _ask(decision_url, request, job, decision_transport)
    except (ValueError, KeyError, TypeError, AttributeError):
        # A malformed answer is the model's; transport errors propagate so the
        # eval does not cache them. No request text in the error.
        ms = (time.perf_counter() - start) * 1000
        return Routed(None, "decision server failed", ms, 0, 0)
    kind, target = answer["choice"], answer["target"]
    out_tokens = 0
    decision, error = None, None
    if kind == "none":
        decision = NoCommand()
    elif kind.startswith("clarify_") and kind.removeprefix("clarify_") in QUESTIONS:
        reason = kind.removeprefix("clarify_")
        decision = parse_decision(
            {"type": "clarify", "reason": reason, "question": QUESTIONS[reason]}
        )
    elif kind == "render":
        decision = Render(include_residual_stem=answer["noul"] >= 0.5)
    elif kind in TARGETED:
        decision = TARGETED[kind](source_id=target)
    elif kind in VALUE:
        decision, error, prompt, out_tokens = _fill(
            request,
            job,
            endpoint,
            kind,
            target,
            escape,
            reasoning_effort,
            llm_transport,
        )
        tokens += prompt
    else:
        error = "decision server failed"
    ms = (time.perf_counter() - start) * 1000
    return Routed(decision, error, ms, tokens, out_tokens, raw=raw)
