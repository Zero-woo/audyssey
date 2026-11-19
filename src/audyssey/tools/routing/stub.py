from audyssey.contracts import (
    Clarify,
    Drop,
    Generate,
    Job,
    Keep,
    NoCommand,
    Render,
    Reseparate,
    SetGain,
    SetPitch,
    Source,
)
from audyssey.tools.routing import Routed

# Keyword baseline for CI plumbing, not an accuracy target. First match wins.
KEYWORDS = [
    ("render", ["저장", "내보내"]),
    ("reseparate", ["다시 분리"]),
    ("generate", ["새로 만들", "생성"]),
    ("keep", ["켜", "살려", "다시 들리"]),
    ("drop", ["꺼", "빼", "없애", "안 들리"]),
    ("down", ["줄여", "작게"]),
    ("up", ["키워", "크게"]),
    ("pitch", ["음높이", "피치"]),
]


def decide(request: str, job: Job):
    text = request.lower()
    action = next((a for a, words in KEYWORDS if any(w in text for w in words)), None)
    if action is None:
        return NoCommand()
    if action == "render":
        return Render()
    targets = [
        s for s in job.sources if any(t in text for t in s.plan.name.lower().split())
    ]
    if len(targets) != 1:
        return Clarify(question="어느 소리를 말씀하시나요?", reason="ambiguous_target")
    return command(action, targets[0], text)


def command(action: str, source: Source, text: str):
    match action:
        case "keep":
            return Keep(source_id=source.id)
        case "drop":
            return Drop(source_id=source.id)
        case "down":
            return SetGain(source_id=source.id, gain=source.gain * 0.5)
        case "up":
            return SetGain(source_id=source.id, gain=min(2, source.gain * 1.5))
        case "pitch":
            return SetPitch(source_id=source.id, semitones=-2 if "낮" in text else 2)
        case "reseparate":
            return Reseparate(source_id=source.id)
        case _:
            return Generate(source_id=source.id)


def route(request: str, job: Job) -> Routed:
    return Routed(decide(request, job), None, 0, 0, 0)
