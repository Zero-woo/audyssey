from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module

from audyssey.contracts import Job, RouteDecision
from audyssey.settings import Settings


@dataclass(frozen=True)
class Routed:
    decision: RouteDecision | None
    error: str | None  # set only when the model's output failed the schema
    latency_ms: float
    input_tokens: int
    output_tokens: int


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


def load_router(settings: Settings) -> Callable[[str, Job], Routed]:
    if settings.router == "stub":
        return import_module("audyssey.tools.routing.stub").route
    raise ValueError(f"router {settings.router!r} is not available yet")
