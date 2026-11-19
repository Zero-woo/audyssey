"""Measure decisio (a Jev-style decision server) as the routing classifier on one split.

Run from the audyssey-router checkout:  uv run python <this file> --url http://127.0.0.1:8000 --out <dir>
Writes raw answers (answers.jsonl) and summary.md with three variants:
  only    value commands (set_gain, set_pitch, add_source) have no values -> counted as invalid
  qwen    value commands take Qwen2.5-3B's cached decision for the same case and rep (real local hybrid)
  ceiling value commands of an allowed type count as right (a perfect value filler; upper bound)
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path

from audyssey.contracts import parse_decision
from audyssey.routing_eval import (
    Run,
    _allowed_types,
    _cache_file,
    _is_invalid,
    _summary,
    bootstrap_ci,
    correct,
    load_cases,
    load_fixture,
    metrics,
)
from audyssey.tools.routing import summarize

ROOT = Path("evals/routing")
DESC = json.loads(Path("src/audyssey/tools/routing/descriptions.json").read_text())["commands"]
VALUE = {"set_gain", "set_pitch", "add_source"}
REASONS = {
    "ambiguous_target": "대상 소스가 둘 이상 해당하거나 \"왼쪽\"처럼 화면 위치로 가리켜 하나로 정할 수 없음",
    "missing_value": "크기나 음높이를 바꾸려는데 양이 없거나 \"조금\"처럼 모호함",
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


def questions(job) -> dict:
    options = {
        name: f"{d['when']} {d['instead']}"
        for name, d in DESC.items()
        if name not in ("clarify", "none")
    }
    options |= {f"clarify_{r}": f"되물어야 함: {t}" for r, t in REASONS.items()}
    options["none"] = f"{DESC['none']['when']} {DESC['none']['instead']}"
    targets = {
        s.id: f"{s.plan.name} ({s.plan.kind}, {'켜짐' if s.keep else '꺼짐'})" for s in job.sources
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


def ask(url: str, state: dict, qs: dict) -> tuple[dict, float]:
    body = json.dumps({"model": "decisio", "state": state, "questions": qs}).encode()
    req = urllib.request.Request(
        f"{url}/v1/systemone", body, {"Content-Type": "application/json"}
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.load(r)
    return out, (time.perf_counter() - start) * 1000


def pick(spec):
    """A number inside a grader bound such as {"ge": 0.4, "le": 0.6}."""
    if not isinstance(spec, dict) or not ({"ge", "gt", "le", "lt"} & spec.keys()):
        return spec
    lo, hi = spec.get("ge", spec.get("gt")), spec.get("le", spec.get("lt"))
    if lo is not None and hi is not None:
        return (lo + hi) / 2
    return lo + 0.01 if lo is not None else hi - 0.01


def to_decision(ans: dict) -> dict | None:
    kind = ans["decision"]["choice"]
    if kind == "none":
        return {"type": "none"}
    if kind.startswith("clarify_"):
        reason = kind.removeprefix("clarify_")
        return {"type": "clarify", "reason": reason, "question": QUESTIONS[reason]}
    if kind == "render":
        return {"type": "render", "include_residual_stem": ans["residual_stem"]["noul"] >= 0.5}
    if kind in VALUE:
        return None
    return {"type": kind, "source_id": ans["target"]["choice"]}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8000")
    p.add_argument("--split", default="dev")
    p.add_argument("--k", type=int, default=5)  # reps of the cached Qwen fallback
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    cases = [c for c in load_cases(ROOT / "cases.jsonl") if c.split == a.split]
    jobs = {c.fixture: load_fixture(ROOT / "fixtures", c.fixture) for c in cases}
    saved = a.out / "answers.jsonl"
    raw = [json.loads(x) for x in saved.read_text().splitlines()] if saved.exists() else []
    for c in cases[len(raw):]:
        job = jobs[c.fixture]
        state = {"job": summarize(job), "request": c.request}
        out, ms = ask(a.url, state, questions(job))
        raw.append({"id": c.id, "latency_ms": ms, "answers": out["answers"], "usage": out.get("usage")})
    (a.out / "answers.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in raw)
    )

    variants: dict[str, list[Run]] = {"only": [], "qwen": [], "ceiling": []}
    for c, r in zip(cases, raw, strict=True):
        job, ans = jobs[c.fixture], r["answers"]
        kind = ans["decision"]["choice"]
        base = to_decision(ans)
        tok = (r.get("usage") or {}).get("input_tokens", 0)
        for rep in range(a.k):
            for name in variants:
                d, ms, err = base, r["latency_ms"], None
                if kind in VALUE:
                    if name == "only":
                        err = "value command needs a value filler"
                    elif name == "qwen":
                        hit = json.loads(
                            _cache_file(ROOT / "cache", "Qwen/Qwen2.5-3B-Instruct", c.id, rep).read_text()
                        )
                        d, ms = hit["decision"], ms + hit["latency_ms"]
                    elif kind in _allowed_types(c):
                        e = next(e for e in c.expected if e["type"] == kind)
                        d = {f: pick(v) for f, v in e.items()}
                        if kind == "add_source":
                            d["plan"] = {"name": "new", "description": "new", **d["plan"]}
                        if "source_id" in d:
                            d["source_id"] = ans["target"]["choice"]
                dec = None if d is None else parse_decision(d)
                variants[name].append(
                    Run(c, rep, dec, err, _is_invalid(job, dec), ms, tok, 0)
                )
    lines = []
    for name, runs in variants.items():
        m = metrics(runs)
        ci = bootstrap_ci(runs)
        (a.out / f"summary-{name}.md").write_text(_summary(m, ci, runs))
        lines.append(
            f"{name}: macro-F1 {m['macro_f1']:.3f} (CI {ci[0]:.3f}-{ci[1]:.3f}), "
            f"pass^k {m['pass_k']:.1%}, p50 {m['latency_p50']:.0f} ms, p95 {m['latency_p95']:.0f} ms"
        )
    type_ok = sum(
        r["answers"]["decision"]["choice"].split("_")[0] in _allowed_types(c)
        if r["answers"]["decision"]["choice"].startswith("clarify_")
        else r["answers"]["decision"]["choice"] in _allowed_types(c)
        for c, r in zip(cases, raw, strict=True)
    )
    lines.append(f"decision type right: {type_ok}/{len(cases)}")
    lines.append(f"routed to value filler: {sum(r['answers']['decision']['choice'] in VALUE for r in raw)}/{len(cases)}")
    print("\n".join(lines))
    (a.out / "summary.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
