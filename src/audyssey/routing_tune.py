"""Offline threshold sweep over a saved run: no router or LLM calls."""

import argparse
import json
from pathlib import Path
from typing import Literal

from audyssey.contracts import parse_decision
from audyssey.routing_eval import Case, Run, correct, load_cases
from audyssey.tools.routing import hybrid

ROOT = Path(__file__).resolve().parents[2] / "evals" / "routing"
GRIDS = {
    "composite": [round(0.3 + 0.1 * i, 2) for i in range(7)],
    "ambiguous_target": [round(0.05 * i, 2) for i in range(1, 11)],
}


def load_runs(run_dir: Path, cases: dict[str, Case]) -> list[Run]:
    runs = []
    for line in (run_dir / "cases.jsonl").read_text().splitlines():
        r = json.loads(line)
        runs.append(
            Run(
                case=cases[r["id"]],
                rep=r["rep"],
                decision=None
                if r["decision"] is None
                else parse_decision(r["decision"]),
                error=r["error"],
                invalid=r["invalid"],
                latency_ms=r["latency_ms"],
                input_tokens=r["input_tokens"],
                output_tokens=r["output_tokens"],
                guarded=r["guarded"],
                raw=r.get("raw"),
            )
        )
    return runs


def sweep(
    runs: list[Run], reason: Literal["composite", "ambiguous_target"], grid: list[float]
) -> list[dict]:
    positive = {"type": "clarify", "reason": reason}
    swapped = parse_decision(
        {"type": "clarify", "reason": reason, "question": hybrid.QUESTIONS[reason]}
    )
    out = []
    for tau in grid:
        tp = fp = fn = fixes = breaks = 0
        for r in runs:
            fired = r.raw is not None and (
                hybrid.override(
                    r.raw["decision"]["choice"],
                    r.raw,
                    tau if reason == "composite" else None,
                    tau if reason == "ambiguous_target" else None,
                )
                == reason
            )
            is_pos = positive in r.case.expected
            tp += fired and is_pos
            fp += fired and not is_pos
            fn += is_pos and not fired
            if fired:
                before, after = correct(r.decision, r.case), correct(swapped, r.case)
                fixes += after and not before
                breaks += before and not after
        den = 2 * tp + fp + fn
        out.append(
            {
                "tau": tau,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "f1": 2 * tp / den if den else 0.0,
                "fixes": fixes,
                "breaks": breaks,
            }
        )
    return out


def pick(results: list[dict]) -> float | None:
    """Best F1, then fewer false positives, then larger tau; None without a net gain."""
    if not results:
        return None
    best = max(results, key=lambda r: (r["f1"], -r["fp"], r["tau"]))
    return best["tau"] if best["fixes"] - best["breaks"] > 0 else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--cases", type=Path, default=ROOT / "cases.jsonl")
    args = ap.parse_args()
    runs = load_runs(args.run_dir, {c.id: c for c in load_cases(args.cases)})
    cols = ("tau", "tp", "fp", "fn", "f1", "fixes", "breaks")
    for reason, grid in GRIDS.items():
        results = sweep(runs, reason, grid)  # ty: ignore[invalid-argument-type]
        print(f"\n{reason}")
        print("  ".join(f"{c:>6}" for c in cols))
        for r in results:
            print(
                "  ".join(
                    f"{r[c]:>6.3f}" if c in ("tau", "f1") else f"{r[c]:>6}"
                    for c in cols
                )
            )
        chosen = pick(results)
        print(f"picked: {'none' if chosen is None else chosen}")


if __name__ == "__main__":
    main()
