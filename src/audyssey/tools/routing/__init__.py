from collections.abc import Callable
from dataclasses import dataclass, replace
from importlib import import_module

from audyssey import graph
from audyssey.contracts import Clarify, Job, NoCommand, RouteDecision
from audyssey.settings import Settings


@dataclass(frozen=True)
class Routed:
    decision: RouteDecision | None
    error: str | None  # set only when the model's output failed the schema
    latency_ms: float
    input_tokens: int
    output_tokens: int
    guarded: bool = False  # the guard replaced the model's answer


def summarize(job: Job) -> dict:
    """The job state a router sees: no descriptions, paths or media."""
    return {
        "silent": job.silent,
        "sources": [
            {
                "id": s.id,
                "name": s.plan.name,
                "kind": s.plan.kind,
                "origin": s.origin,
                "replaces": s.replaces,
                "keep": s.keep,
                "gain": s.gain,
                "pitch_semitones": s.pitch_semitones,
            }
            for s in job.sources
        ],
        "residual": {
            "id": "residual",
            "keep": job.residual.keep,
            "gain": job.residual.gain,
        },
    }


UNSUPPORTED = {
    "dialogue is not generated": "대사는 새로 만들 수 없어요.",
    "residual cannot be generated": "나머지 소리는 새로 만들 수 없어요.",
    "residual does not support pitch": "나머지 소리는 음높이를 바꿀 수 없어요.",
    "residual cannot be reseparated": "나머지 소리는 다시 분리할 수 없어요.",
    "generated sources and silent videos cannot be reseparated": (
        "생성한 소리나 소리가 없는 영상은 다시 분리할 수 없어요."
    ),
    "silent videos only support generation": (
        "소리가 없는 영상이라 원본에서 분리할 수 없어요. 새로 만들 수는 있어요."
    ),
    "source name already exists; use reseparate": "같은 이름의 소리가 이미 있어요.",
}


def guard(job: Job, routed: Routed) -> Routed:
    """Replace a command the job cannot run with a clarify answer."""
    decision = routed.decision
    if decision is None or isinstance(decision, Clarify | NoCommand):
        return routed
    try:
        graph.check_command(job, decision)
    except KeyError:
        clarify = Clarify(
            question="어느 소리를 말씀하시나요?", reason="ambiguous_target"
        )
    except ValueError as e:
        text = UNSUPPORTED.get(str(e), "그 편집은 지금 할 수 없어요.")
        clarify = Clarify(question=text, reason="unsupported")
    else:
        return routed
    return replace(routed, decision=clarify, guarded=True)


def model_name(settings: Settings) -> str:
    """Names the whole pipeline; it keys the eval cache and config.json."""
    if settings.router == "stub":
        return "stub"
    model = settings.router_endpoint().model
    if settings.router != "hybrid":
        return model
    escape = "+escape" if settings.router_hybrid_escape else ""
    return f"hybrid[{settings.router_decision_model}+{model}{escape}]"


def load_router(settings: Settings) -> Callable[[str, Job], Routed]:
    route = _load_route(settings)
    if not settings.router_guard:
        return route
    return lambda request, job: guard(job, route(request, job))


def _load_route(settings: Settings) -> Callable[[str, Job], Routed]:
    if settings.router == "stub":
        return import_module("audyssey.tools.routing.stub").route
    if settings.router == "hybrid":
        hybrid_route = import_module("audyssey.tools.routing.hybrid").route
        url, endpoint = settings.router_decision_url, settings.router_endpoint()
        escape, effort = settings.router_hybrid_escape, settings.router_reasoning_effort
        return lambda request, job: hybrid_route(
            request, job, url, endpoint, escape=escape, reasoning_effort=effort
        )
    real_route = import_module("audyssey.tools.routing.real").route
    endpoint = settings.router_endpoint()
    effort = settings.router_reasoning_effort
    fmt = settings.router_format
    return lambda request, job: real_route(
        request, job, endpoint, reasoning_effort=effort, fmt=fmt
    )
