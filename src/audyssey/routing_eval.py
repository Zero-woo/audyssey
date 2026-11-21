"""Routing evaluation set: case format, fixtures, splits and labeler agreement."""

import hashlib
import json
import math
import random
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

from pydantic import TypeAdapter, field_validator

from audyssey import graph
from audyssey.contracts import (
    Clarify,
    Job,
    Model,
    NoCommand,
    RouteDecision,
    parse_decision,
)
from audyssey.tools import routing
from audyssey.tools.routing import Routed


DECISION_TYPES = set(
    TypeAdapter(RouteDecision).json_schema()["discriminator"]["mapping"]
)
CLARIFY_REASONS = set(get_args(Clarify.model_fields["reason"].annotation))


class Case(Model):
    id: str
    fixture: Literal["F1", "F2", "F3", "F4", "F5"]
    request: str
    category: Literal[
        "positive", "none", "near_miss", "clarify", "constraint", "composite"
    ]
    pair: str | None = None
    template: str
    expected: list[dict]
    split: Literal["train", "dev", "test"] | None = None

    @field_validator("expected")
    @classmethod
    def _check_expected(cls, expected: list[dict]) -> list[dict]:
        for entry in expected:
            if entry.get("type") not in DECISION_TYPES:
                raise ValueError(f"unknown expected type: {entry.get('type')!r}")
            if (
                entry["type"] == "clarify"
                and entry.get("reason", "other") not in CLARIFY_REASONS
            ):
                raise ValueError(f"unknown clarify reason: {entry['reason']!r}")
        return expected


def load_cases(path: Path) -> list[Case]:
    return [
        Case.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def load_fixture(root: Path, name: str) -> Job:
    return Job.model_validate_json((root / f"{name}.json").read_text())


def assign_splits(cases: list[Case], seed: int = 0) -> list[Case]:
    """Split by template (never by case) within each category, about 40/30/30."""
    templates: dict[str, set[str]] = defaultdict(set)
    category_of: dict[str, str] = {}
    for c in cases:
        if category_of.setdefault(c.template, c.category) != c.category:
            raise ValueError(
                f"template {c.template!r} appears under more than one category"
            )
        templates[c.category].add(c.template)
    split_of: dict[tuple[str, str], Literal["train", "dev", "test"]] = {}
    rng = random.Random(seed)
    for category in sorted(templates):
        names = sorted(templates[category])
        rng.shuffle(names)
        n_train = round(len(names) * 0.4)
        n_dev = round(len(names) * 0.3)
        for i, t in enumerate(names):
            split_of[category, t] = (
                "train" if i < n_train else "dev" if i < n_train + n_dev else "test"
            )
    return [
        c.model_copy(update={"split": split_of[c.category, c.template]}) for c in cases
    ]


def blank_labels(cases: list[Case]) -> list[dict]:
    return [{"id": c.id, "fixture": c.fixture, "request": c.request} for c in cases]


def kappa(a: list[str], b: list[str]) -> float:
    """Cohen's kappa for two labelers' category labels."""
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    chance = sum(ca[k] * cb[k] for k in ca) / n**2
    if chance == 1:
        return 1.0
    return (observed - chance) / (1 - chance)


COMMANDS = (
    "keep",
    "drop",
    "set_gain",
    "set_pitch",
    "reseparate",
    "generate",
    "add_source",
    "render",
)
LABELS = (*COMMANDS, "clarify", "none")
_RANGE_KEYS = {"lt", "le", "ge", "gt"}


def value_ok(actual: float, spec: float | dict[str, float]) -> bool:
    """A number must be equal; a dict must satisfy every lt/le/ge/gt bound."""
    if not isinstance(spec, dict):
        return actual == spec
    return (
        ("lt" not in spec or actual < spec["lt"])
        and ("le" not in spec or actual <= spec["le"])
        and ("ge" not in spec or actual >= spec["ge"])
        and ("gt" not in spec or actual > spec["gt"])
    )


def _match(actual: dict, expected: dict, skip: set[str]) -> bool:
    for key, spec in expected.items():
        if key in skip:
            continue
        if key not in actual:
            return False
        got = actual[key]
        if isinstance(spec, dict) and spec and set(spec) <= _RANGE_KEYS:
            if isinstance(got, bool) or not isinstance(got, int | float):
                return False
            if not value_ok(got, spec):
                return False
        elif isinstance(spec, dict):
            if not isinstance(got, dict) or not _match(got, spec, set()):
                return False
        elif isinstance(spec, int | float) and not isinstance(spec, bool):
            if isinstance(got, bool) or not isinstance(got, int | float):
                return False
            if not value_ok(got, spec):
                return False
        elif got != spec:
            return False
    return True


def correct(decision: RouteDecision | None, case: Case) -> bool:
    """True if the decision matches any allowed answer; no answer allowed means none."""
    if decision is None:
        return False
    if not case.expected:
        return decision.type == "none"
    d = decision.model_dump()
    skip = set() if case.category == "clarify" else {"reason"}
    return any(_match(d, e, skip) for e in case.expected)


@dataclass
class Run:
    case: Case
    rep: int
    decision: RouteDecision | None
    error: str | None
    invalid: bool  # check_command raised for a command decision
    latency_ms: float
    input_tokens: int
    output_tokens: int
    guarded: bool = False
    raw: dict | None = None
    broke: bool = False  # raw answer was correct, guarded one is not


def _allowed_types(case: Case) -> set[str]:
    return {e["type"] for e in case.expected} or {"none"}


def _labels(run: Run) -> tuple[str, str]:
    """(gold, predicted); a schema error predicts "invalid"."""
    pred = "invalid" if run.decision is None else run.decision.type
    if correct(run.decision, run.case):
        return pred, pred
    return (run.case.expected[0]["type"] if run.case.expected else "none"), pred


def _rate(num: int, den: int) -> float | None:
    return num / den if den else None


def _percentile(values: list[float], q: float) -> float | None:
    """Nearest rank: the ceil(q * n)-th smallest value."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(math.ceil(q * len(ordered)), 1) - 1]


def _per_label(pairs: list[tuple[str, str]]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for label in LABELS:
        tp = sum(g == label and p == label for g, p in pairs)
        fp = sum(g != label and p == label for g, p in pairs)
        fn = sum(g == label and p != label for g, p in pairs)
        out[label] = {
            "precision": _rate(tp, tp + fp),
            "recall": _rate(tp, tp + fn),
            "f1": _rate(2 * tp, 2 * tp + fp + fn),
            "support": tp + fn,
        }
    return out


def _macro_f1(runs: list[Run]) -> float | None:
    stats = _per_label([_labels(r) for r in runs]).values()
    f1s = [s["f1"] for s in stats if s["support"]]
    return sum(f1s) / len(f1s) if f1s else None


def metrics(runs: list[Run]) -> dict:
    pairs = [_labels(r) for r in runs]
    confusion: dict[str, dict[str, int]] = {}
    for g, p in pairs:
        confusion.setdefault(g, {}).setdefault(p, 0)
        confusion[g][p] += 1
    ok = [correct(r.decision, r.case) for r in runs]

    def where(pred) -> list[int]:
        return [i for i, r in enumerate(runs) if pred(r)]

    none_runs = where(lambda r: r.case.category == "none")
    clarify_runs = where(lambda r: r.case.category == "clarify")
    no_clarify = where(lambda r: "clarify" not in _allowed_types(r.case))
    typed = where(
        lambda r: r.decision is not None and r.decision.type in _allowed_types(r.case)
    )
    pair_runs: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(runs):
        if r.case.category == "near_miss" and r.case.pair is not None:
            pair_runs[r.case.pair].append(i)
    by_case: dict[str, list[bool]] = defaultdict(list)
    for r, o in zip(runs, ok, strict=True):
        by_case[r.case.id].append(o)
    latencies = [r.latency_ms for r in runs]
    return {
        "per_label": _per_label(pairs),
        "macro_f1": _macro_f1(runs),
        "confusion": confusion,
        "none_suppression": _rate(
            sum(pairs[i][1] == "none" for i in none_runs), len(none_runs)
        ),
        "over_call": _rate(
            sum(pairs[i][1] in COMMANDS for i in none_runs), len(none_runs)
        ),
        "clarify_hit": _rate(sum(ok[i] for i in clarify_runs), len(clarify_runs)),
        "unnecessary_clarify": _rate(
            sum(pairs[i][1] == "clarify" for i in no_clarify), len(no_clarify)
        ),
        "pair_accuracy": {
            k: sum(ok[i] for i in v) / len(v) for k, v in pair_runs.items()
        },
        "param_error": _rate(sum(not ok[i] for i in typed), len(typed)),
        "invalid_rate": _rate(
            sum(r.error is not None or r.invalid for r in runs), len(runs)
        ),
        "pass_k": _rate(sum(all(v) for v in by_case.values()), len(by_case)),
        "latency_p50": _percentile(latencies, 0.5),
        "latency_p95": _percentile(latencies, 0.95),
        "input_tokens": sum(r.input_tokens for r in runs),
        "output_tokens": sum(r.output_tokens for r in runs),
        "runs": len(runs),
        "cases": len(by_case),
    }


def adopt(new: dict, old: dict) -> list[str]:
    """Reasons a change fails the adoption rule; an empty list means adopt."""
    fails = []
    if new["macro_f1"] <= old["macro_f1"]:
        fails.append("macro-F1 did not rise")
    for label, o in old["per_label"].items():
        n = new["per_label"][label]["recall"]
        if o["recall"] is not None and n is not None and o["recall"] - n > 0.03 + 1e-9:
            fails.append(f"{label} recall fell {o['recall']:.3f} -> {n:.3f}")
    o, n = old["none_suppression"], new["none_suppression"]
    if o is not None and n is not None and n < o:
        fails.append(f"none_suppression fell {o:.3f} -> {n:.3f}")
    return fails


def bootstrap_ci(runs: list[Run], n: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% percentile CI of macro-F1, resampling templates with replacement."""
    by_template: dict[str, list[Run]] = defaultdict(list)
    for r in runs:
        by_template[r.case.template].append(r)
    groups = list(by_template.values())
    rng = random.Random(seed)
    scores: list[float] = []
    for _ in range(n):
        drawn = [r for g in rng.choices(groups, k=len(groups)) for r in g]
        score = _macro_f1(drawn)
        if score is not None:
            scores.append(score)
    lo, hi = _percentile(scores, 0.025), _percentile(scores, 0.975)
    if lo is None or hi is None:
        raise ValueError("no runs to bootstrap")
    return lo, hi


DESCRIPTIONS = Path(routing.__file__).parent / "descriptions.json"
INPUT_TOKENS_PER_CALL = 2300
_CACHED_FIELDS = ("error", "latency_ms", "input_tokens", "output_tokens")


def _descriptions() -> tuple[str, int]:
    raw = DESCRIPTIONS.read_bytes()
    return hashlib.sha256(raw).hexdigest(), json.loads(raw)["version"]


def descriptions_sha(descriptions: dict | None) -> str:
    if descriptions is None:
        return _descriptions()[0]
    text = json.dumps(descriptions, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def _cache_file(
    cache: Path,
    model: str,
    case_id: str,
    rep: int,
    fmt: str,
    effort: str | None = None,
    salt: str = "",
    descriptions: dict | None = None,
) -> Path:
    ids = [salt, case_id] if salt else [case_id]
    key = json.dumps([model, fmt, effort, descriptions_sha(descriptions), *ids, rep])
    return cache / f"{hashlib.sha256(key.encode()).hexdigest()}.json"


def uncached_calls(
    model: str,
    cases: list[Case],
    k: int,
    cache: Path,
    fmt: str = "tools",
    effort: str | None = None,
    salt: str = "",
    descriptions: dict | None = None,
) -> int:
    return sum(
        not _cache_file(
            cache, model, c.id, rep, fmt, effort, salt, descriptions
        ).exists()
        for c in cases
        for rep in range(k)
    )


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return out.stdout.strip()


def _is_invalid(job: Job, decision: RouteDecision | None) -> bool:
    if decision is None or isinstance(decision, Clarify | NoCommand):
        return False
    try:
        graph.check_command(job, decision)
    except (KeyError, ValueError):
        return True
    return False


def _run_one(
    router: Callable[[str, Job], Routed],
    model: str,
    case: Case,
    job: Job,
    rep: int,
    cache: Path | None,
    fmt: str,
    guard: bool = False,
    effort: str | None = None,
    salt: str = "",
    descriptions: dict | None = None,
) -> Run:
    hit: dict
    path = (
        None
        if cache is None
        else _cache_file(cache, model, case.id, rep, fmt, effort, salt, descriptions)
    )
    if path is not None and path.exists():
        hit = json.loads(path.read_text())
    else:
        routed = router(case.request, job)
        hit = {
            "decision": None
            if routed.decision is None
            else routed.decision.model_dump(),
            **{f: getattr(routed, f) for f in _CACHED_FIELDS},
            "raw": routed.raw,
        }
        if cache is not None and path is not None:
            cache.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(hit))
    decision = None if hit["decision"] is None else parse_decision(hit["decision"])
    raw_ok = correct(decision, case)
    guarded = False
    if guard:
        # Applied after the cache: the cache keeps the router's raw answer.
        out = routing.guard(job, Routed(decision, *(hit[f] for f in _CACHED_FIELDS)))
        decision, guarded = out.decision, out.guarded
    return Run(
        case=case,
        rep=rep,
        decision=decision,
        error=hit["error"],
        invalid=_is_invalid(job, decision),
        latency_ms=hit["latency_ms"],
        input_tokens=hit["input_tokens"],
        output_tokens=hit["output_tokens"],
        guarded=guarded,
        raw=hit.get("raw"),
        broke=raw_ok and not correct(decision, case),
    )


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def _summary(m: dict, ci: tuple[float, float], runs: list[Run]) -> str:
    rows = [
        ("macro-F1", f"{m['macro_f1']:.3f} (95% CI {ci[0]:.3f} to {ci[1]:.3f})"),
        ("none suppression", _pct(m["none_suppression"])),
        ("over-call", _pct(m["over_call"])),
        ("clarify hit", _pct(m["clarify_hit"])),
        ("unnecessary clarify", _pct(m["unnecessary_clarify"])),
        ("param error", _pct(m["param_error"])),
        ("invalid rate", _pct(m["invalid_rate"])),
        ("pass^k", _pct(m["pass_k"])),
        ("latency p50 / p95 (ms)", f"{m['latency_p50']:.0f} / {m['latency_p95']:.0f}"),
        ("input / output tokens", f"{m['input_tokens']} / {m['output_tokens']}"),
        ("runs / cases", f"{m['runs']} / {m['cases']}"),
        ("guard fired", _pct(_rate(sum(r.guarded for r in runs), len(runs)))),
        ("guard broke", str(sum(r.broke for r in runs))),
    ]
    lines = ["# Routing eval", "", "| metric | value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in rows]
    pairs = sorted(m["pair_accuracy"].items())
    if pairs:
        lines += [
            "",
            "## Near-miss pair accuracy",
            "",
            "| pair | accuracy |",
            "|---|---|",
        ]
        lines += [f"| {k} | {_pct(v)} |" for k, v in pairs]
    preds = sorted({p for row in m["confusion"].values() for p in row})
    lines += ["", "## Confusion (rows gold, columns predicted)", ""]
    lines += ["| gold | " + " | ".join(preds) + " |", "|---|" + "---|" * len(preds)]
    for gold in sorted(m["confusion"]):
        counts = [str(m["confusion"][gold].get(p, 0)) for p in preds]
        lines.append(f"| {gold} | " + " | ".join(counts) + " |")
    failed = [r for r in runs if not correct(r.decision, r.case)][:10]
    lines += ["", "## Failed examples", ""]
    for r in failed:
        got = "invalid" if r.decision is None else r.decision.model_dump_json()
        lines.append(
            f"- {r.case.id} (rep {r.rep}): request {r.case.request!r}; "
            f"expected {json.dumps(r.case.expected, ensure_ascii=False)}; got {got}"
        )
    return "\n".join(lines) + "\n"


def run_eval(
    router: Callable[[str, Job], Routed],
    model: str,
    router_name: str,
    cases: list[Case],
    fixtures: Path,
    k: int,
    out: Path,
    cache: Path | None,
    fmt: str = "tools",
    guard: bool = False,
    effort: str | None = None,
    salt: str = "",
    descriptions: dict | None = None,
) -> dict:
    """Route every case k times (cached), grade, and write results to a new out dir."""
    if out.exists():
        raise FileExistsError(out)
    jobs = {c.fixture: load_fixture(fixtures, c.fixture) for c in cases}
    runs = [
        _run_one(
            router,
            model,
            c,
            jobs[c.fixture],
            rep,
            cache,
            fmt,
            guard,
            effort,
            salt,
            descriptions,
        )
        for c in cases
        for rep in range(k)
    ]
    m = metrics(runs)
    out.mkdir(parents=True)
    sha = descriptions_sha(descriptions)
    version = (
        _descriptions()[1] if descriptions is None else descriptions.get("version")
    )
    (out / "cases.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "id": r.case.id,
                    "rep": r.rep,
                    "request": r.case.request,
                    "expected": r.case.expected,
                    "decision": None if r.decision is None else r.decision.model_dump(),
                    "error": r.error,
                    "invalid": r.invalid,
                    "correct": correct(r.decision, r.case),
                    "latency_ms": r.latency_ms,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "guarded": r.guarded,
                    "raw": r.raw,
                },
                ensure_ascii=False,
            )
            + "\n"
            for r in runs
        )
    )
    (out / "config.json").write_text(
        json.dumps(
            {
                "model": model,
                "router": router_name,
                "format": fmt,
                "guard": guard,
                "reasoning_effort": effort,
                "descriptions_version": version,
                "descriptions_sha256": sha,
                "git_sha": git_sha(),
                "k": k,
                "split": cases[0].split,
                "date": datetime.now(UTC).isoformat(),
                "cases": len(cases),
            },
            indent=2,
        )
    )
    (out / "summary.md").write_text(_summary(m, bootstrap_ci(runs), runs))
    return m
