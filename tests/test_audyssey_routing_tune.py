import tempfile
import unittest
from pathlib import Path

from audyssey.contracts import parse_decision
from audyssey.routing_eval import Case, Run, load_cases, metrics, run_eval
from audyssey.routing_tune import load_runs, pick, sweep
from audyssey.tools.routing import Routed

ROOT = Path(__file__).resolve().parent.parent / "evals" / "routing"


def case(i: str, expected: list[dict]) -> Case:
    return Case.model_validate(
        {
            "id": i,
            "fixture": "F1",
            "request": "r",
            "category": "composite",
            "template": i,
            "expected": expected,
        }
    )


def answers(kind: str, composite: float) -> dict:
    return {
        "decision": {"choice": kind},
        "composite": {"noul": composite},
        "target": {"probabilities": {"a": 0.9, "b": 0.1}},
    }


def run(i: str, expected: list[dict], kind: str, composite: float) -> Run:
    decision = (
        parse_decision({"type": "keep", "source_id": "a"})
        if kind == "keep"
        else parse_decision({"type": "none"})
    )
    return Run(
        case(i, expected), 0, decision, None, False, 1.0, 1, 1, raw=answers(kind, composite)
    )


COMP = [{"type": "clarify", "reason": "composite"}]
KEEP = [{"type": "keep", "source_id": "a"}]


class SweepTests(unittest.TestCase):
    def test_counts(self) -> None:
        runs = [
            run("p1", COMP, "keep", 0.9),  # positive, fires at 0.5 -> tp, fix
            run("p2", COMP, "keep", 0.2),  # positive, silent -> fn
            run("n1", KEEP, "keep", 0.7),  # negative, fires -> fp, break
            run("n2", KEEP, "keep", 0.1),  # negative, silent
            run("n3", [], "none", 0.99),  # none never overridden
        ]
        by = {r["tau"]: r for r in sweep(runs, "composite", [0.5, 0.95])}
        self.assertEqual(
            {k: by[0.5][k] for k in ("tp", "fp", "fn", "fixes", "breaks")},
            {"tp": 1, "fp": 1, "fn": 1, "fixes": 1, "breaks": 1},
        )
        self.assertAlmostEqual(by[0.5]["f1"], 0.5)
        self.assertEqual(
            {k: by[0.95][k] for k in ("tp", "fp", "fn", "fixes", "breaks")},
            {"tp": 0, "fp": 0, "fn": 2, "fixes": 0, "breaks": 0},
        )
        self.assertEqual(by[0.95]["f1"], 0.0)


class PickTests(unittest.TestCase):
    def row(self, tau, f1, fp=0, fixes=1, breaks=0) -> dict:
        return {"tau": tau, "f1": f1, "fp": fp, "fixes": fixes, "breaks": breaks}

    def test_best_f1(self) -> None:
        self.assertEqual(pick([self.row(0.3, 0.5), self.row(0.4, 0.8)]), 0.4)

    def test_ties_fewer_fp_then_larger_tau(self) -> None:
        self.assertEqual(pick([self.row(0.3, 0.8, 2), self.row(0.4, 0.8, 1)]), 0.4)
        self.assertEqual(pick([self.row(0.3, 0.8, 1), self.row(0.4, 0.8, 1)]), 0.4)
        self.assertEqual(pick([self.row(0.5, 0.8, 1), self.row(0.4, 0.8, 1)]), 0.5)

    def test_none_when_no_net_gain(self) -> None:
        self.assertIsNone(pick([self.row(0.3, 0.8, fixes=2, breaks=2)]))


class LoadRunsTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        cases = load_cases(ROOT / "cases.jsonl")[:6]
        raw = answers("none", 0.1)

        def router(request: str, job) -> Routed:
            return Routed(parse_decision({"type": "none"}), None, 5.0, 10, 2, raw=raw)

        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "o"
            m = run_eval(router, "m", "real", cases, ROOT / "fixtures", 2, out, None)
            runs = load_runs(out, {c.id: c for c in cases})
            self.assertEqual(metrics(runs), m)
            self.assertEqual(runs[0].raw, raw)


if __name__ == "__main__":
    unittest.main()
