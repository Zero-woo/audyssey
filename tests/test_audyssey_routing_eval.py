import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError

from audyssey.contracts import Job, parse_decision
from audyssey.routing_eval import (
    Case,
    Run,
    assign_splits,
    blank_labels,
    bootstrap_ci,
    correct,
    kappa,
    load_cases,
    load_fixture,
    metrics,
    value_ok,
)

ROOT = Path(__file__).resolve().parent.parent / "evals" / "routing"
FIXTURES = ROOT / "fixtures"


def make_case(i: int, template: str, category: str = "positive") -> Case:
    return Case.model_validate(
        {
            "id": f"c{i}",
            "fixture": "F1",
            "request": "req",
            "category": category,
            "template": template,
            "expected": [],
        }
    )


class FixtureTests(unittest.TestCase):
    def test_all_fixtures_validate(self) -> None:
        for name in ("F1", "F2", "F3", "F4", "F5"):
            text = (FIXTURES / f"{name}.json").read_text()
            self.assertEqual(Job.model_validate_json(text), load_fixture(FIXTURES, name))

    def test_f4_is_silent_and_generated(self) -> None:
        job = load_fixture(FIXTURES, "F4")
        self.assertTrue(job.silent)
        self.assertTrue(all(s.origin == "generated" for s in job.sources))

    def test_f5_has_off_and_attenuated_sources(self) -> None:
        job = load_fixture(FIXTURES, "F5")
        self.assertTrue(any(not s.keep for s in job.sources))
        self.assertTrue(any(s.gain == 0.3 for s in job.sources))


class LoadCasesTests(unittest.TestCase):
    def load(self, **override: object) -> list[Case]:
        line = {
            "id": "x",
            "fixture": "F1",
            "request": "r",
            "category": "none",
            "pair": None,
            "template": "t",
            "expected": [],
            "split": None,
        } | override
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "cases.jsonl"
            path.write_text(json.dumps(line) + "\n")
            return load_cases(path)

    def test_valid_line(self) -> None:
        self.assertEqual(self.load()[0].id, "x")

    def test_unknown_fixture(self) -> None:
        with self.assertRaises(ValidationError):
            self.load(fixture="F9")

    def test_unknown_category(self) -> None:
        with self.assertRaises(ValidationError):
            self.load(category="weird")

    def test_shipped_examples_load(self) -> None:
        cases = load_cases(ROOT / "cases.jsonl")
        self.assertEqual([c.id for c in cases], [f"ex-{i}" for i in range(1, 6)])


class SplitTests(unittest.TestCase):
    def cases(self) -> list[Case]:
        out = []
        for cat in ("positive", "none"):
            for t in range(10):
                for k in range(2):
                    out.append(make_case(len(out), f"{cat}-{t}", cat))
        return out

    def test_same_template_same_split(self) -> None:
        by_t = defaultdict(set)
        for c in assign_splits(self.cases()):
            by_t[c.template].add(c.split)
        self.assertTrue(all(len(v) == 1 and None not in v for v in by_t.values()))

    def test_deterministic_and_order_independent(self) -> None:
        cases = self.cases()
        a = assign_splits(cases)
        self.assertEqual(a, assign_splits(cases))
        b = assign_splits(list(reversed(cases)))
        self.assertEqual({c.id: c.split for c in a}, {c.id: c.split for c in b})

    def test_template_in_two_categories_rejected(self) -> None:
        cases = [make_case(1, "shared", "positive"), make_case(2, "shared", "none")]
        with self.assertRaisesRegex(ValueError, "shared"):
            assign_splits(cases)

    def test_ratio_per_category(self) -> None:
        for cat in ("positive", "none"):
            templates = defaultdict(set)
            for c in assign_splits(self.cases()):
                if c.category == cat:
                    templates[c.split].add(c.template)
            for split, share in (("train", 4), ("dev", 3), ("test", 3)):
                self.assertLessEqual(abs(len(templates[split]) - share), 1)


class BlankAndKappaTests(unittest.TestCase):
    def test_blank_labels_hides_answers(self) -> None:
        rows = blank_labels([make_case(1, "t")])
        self.assertEqual(rows, [{"id": "c1", "fixture": "F1", "request": "req"}])

    def test_kappa_perfect(self) -> None:
        self.assertEqual(kappa(["a", "a", "b", "b"], ["a", "a", "b", "b"]), 1.0)

    def test_kappa_chance(self) -> None:
        self.assertEqual(kappa(["a", "b", "a", "b"], ["a", "a", "b", "b"]), 0.0)


if __name__ == "__main__":
    unittest.main()


def gcase(
    cid: str,
    category: str,
    expected: list[dict],
    pair: str | None = None,
    template: str | None = None,
) -> Case:
    return Case.model_validate(
        {
            "id": cid,
            "fixture": "F1",
            "request": "req",
            "category": category,
            "pair": pair,
            "template": template or f"t-{cid}",
            "expected": expected,
        }
    )


def grun(
    case: Case,
    decision: dict | None,
    rep: int = 0,
    error: str | None = None,
    invalid: bool = False,
    latency_ms: float = 0.0,
) -> Run:
    return Run(
        case=case,
        rep=rep,
        decision=None if decision is None else parse_decision(decision),
        error=error,
        invalid=invalid,
        latency_ms=latency_ms,
        input_tokens=10,
        output_tokens=1,
    )


GAIN_LT_1 = [{"type": "set_gain", "source_id": "s1", "gain": {"lt": 1.0}}]
SET_GAIN = {"type": "set_gain", "source_id": "s1", "gain": 0.5}
DROP_S1 = {"type": "drop", "source_id": "s1"}
CLARIFY_AMBIG = {"type": "clarify", "question": "q", "reason": "ambiguous_target"}
CLARIFY_OTHER = {"type": "clarify", "question": "q", "reason": "other"}
NONE = {"type": "none"}


class GradingTests(unittest.TestCase):
    def test_value_ok(self) -> None:
        self.assertTrue(value_ok(1.0, 1.0))
        self.assertFalse(value_ok(1.0, 0.5))
        self.assertTrue(value_ok(0.5, {"lt": 1.0, "ge": 0.5}))
        self.assertFalse(value_ok(1.0, {"lt": 1.0}))
        self.assertTrue(value_ok(1.0, {"le": 1.0, "gt": 0.0}))
        self.assertFalse(value_ok(0.0, {"gt": 0.0}))

    def test_second_allowed_entry_matches(self) -> None:
        c = gcase("b", "positive", [DROP_S1, {"type": "set_gain", "source_id": "s1", "gain": {"le": 0}}])
        self.assertTrue(correct(parse_decision({**SET_GAIN, "gain": 0}), c))

    def test_range_boundary_is_wrong(self) -> None:
        c = gcase("a", "positive", GAIN_LT_1)
        self.assertTrue(correct(parse_decision(SET_GAIN), c))
        self.assertFalse(correct(parse_decision({**SET_GAIN, "gain": 1.0}), c))

    def test_source_id_and_type_must_match(self) -> None:
        c = gcase("a", "positive", [DROP_S1])
        self.assertFalse(correct(parse_decision({**DROP_S1, "source_id": "s9"}), c))
        self.assertFalse(correct(parse_decision({"type": "keep", "source_id": "s1"}), c))

    def test_none_decision_and_none_category(self) -> None:
        self.assertFalse(correct(None, gcase("n", "none", [])))
        self.assertTrue(correct(parse_decision(NONE), gcase("n", "none", [])))
        self.assertFalse(correct(parse_decision(DROP_S1), gcase("n", "none", [])))

    def test_clarify_reason_only_compared_in_clarify_category(self) -> None:
        exp = [{"type": "clarify", "reason": "ambiguous_target"}]
        self.assertFalse(correct(parse_decision(CLARIFY_OTHER), gcase("e", "clarify", exp)))
        self.assertTrue(correct(parse_decision(CLARIFY_AMBIG), gcase("e", "clarify", exp)))
        self.assertTrue(correct(parse_decision(CLARIFY_OTHER), gcase("e", "positive", exp)))

    def test_nested_subset_and_missing_key(self) -> None:
        plan = {"name": "bird", "kind": "sfx", "description": "chirp"}
        c = gcase("p", "positive", [{"type": "add_source", "plan": {"kind": "sfx"}}])
        self.assertTrue(correct(parse_decision({"type": "add_source", "plan": plan}), c))
        c2 = gcase("p", "positive", [{"type": "add_source", "plan": {"kind": "speech"}}])
        self.assertFalse(correct(parse_decision({"type": "add_source", "plan": plan}), c2))
        c3 = gcase("p", "positive", [{"type": "drop", "nope": 1}])
        self.assertFalse(correct(parse_decision(DROP_S1), c3))


def ten_runs() -> list[Run]:
    a = gcase("A", "positive", GAIN_LT_1)
    b = gcase("B", "positive", [DROP_S1, {"type": "set_gain", "source_id": "s1", "gain": {"le": 0}}])
    c = gcase("C", "none", [])
    d = gcase("D", "near_miss", [DROP_S1], pair="drop|set_gain")
    e = gcase("E", "clarify", [{"type": "clarify", "reason": "ambiguous_target"}])
    f = gcase("F", "positive", [{"type": "drop", "source_id": "s2"}])
    g = gcase("G", "none", [])
    e2 = gcase("E2", "clarify", [{"type": "clarify", "reason": "ambiguous_target"}])
    h = gcase("H", "positive", [{"type": "keep", "source_id": "s1"}])
    i = gcase("I", "positive", [DROP_S1])
    return [
        grun(a, {**SET_GAIN, "gain": 1.0}, latency_ms=100),
        grun(b, {**SET_GAIN, "gain": 0}, latency_ms=200),
        grun(c, NONE, latency_ms=300),
        grun(d, SET_GAIN, latency_ms=400),
        grun(e, CLARIFY_OTHER, latency_ms=500),
        grun(f, {"type": "drop", "source_id": "s9"}, invalid=True, latency_ms=600),
        grun(g, SET_GAIN, latency_ms=700),
        grun(e2, CLARIFY_AMBIG, latency_ms=800),
        grun(h, CLARIFY_AMBIG, latency_ms=900),
        grun(i, None, error="bad json", latency_ms=1000),
    ]


class MetricsTests(unittest.TestCase):
    def test_metrics_on_ten_runs(self) -> None:
        m = metrics(ten_runs())
        self.assertEqual(m["runs"], 10)
        self.assertEqual(m["cases"], 10)
        self.assertEqual(
            m["confusion"],
            {
                "set_gain": {"set_gain": 2},
                "none": {"none": 1, "set_gain": 1},
                "drop": {"set_gain": 1, "drop": 1, "invalid": 1},
                "clarify": {"clarify": 2},
                "keep": {"clarify": 1},
            },
        )
        pl = m["per_label"]
        self.assertAlmostEqual(pl["set_gain"]["precision"], 1 / 2)
        self.assertAlmostEqual(pl["set_gain"]["recall"], 1.0)
        self.assertAlmostEqual(pl["set_gain"]["f1"], 2 / 3)
        self.assertEqual(pl["set_gain"]["support"], 2)
        self.assertAlmostEqual(pl["none"]["f1"], 2 / 3)
        self.assertAlmostEqual(pl["drop"]["precision"], 1.0)
        self.assertAlmostEqual(pl["drop"]["recall"], 1 / 3)
        self.assertAlmostEqual(pl["drop"]["f1"], 1 / 2)
        self.assertAlmostEqual(pl["clarify"]["precision"], 2 / 3)
        self.assertAlmostEqual(pl["clarify"]["f1"], 4 / 5)
        self.assertIsNone(pl["keep"]["precision"])
        self.assertAlmostEqual(pl["keep"]["recall"], 0.0)
        self.assertAlmostEqual(pl["keep"]["f1"], 0.0)
        self.assertEqual(pl["render"], {"precision": None, "recall": None, "f1": None, "support": 0})
        self.assertAlmostEqual(m["macro_f1"], (2 / 3 + 2 / 3 + 1 / 2 + 4 / 5 + 0) / 5)
        self.assertAlmostEqual(m["none_suppression"], 1 / 2)
        self.assertAlmostEqual(m["over_call"], 1 / 2)
        self.assertAlmostEqual(m["clarify_hit"], 1 / 2)
        self.assertAlmostEqual(m["unnecessary_clarify"], 1 / 8)
        self.assertEqual(m["pair_accuracy"], {"drop|set_gain": 0.0})
        self.assertAlmostEqual(m["param_error"], 3 / 6)
        self.assertAlmostEqual(m["invalid_rate"], 2 / 10)
        self.assertAlmostEqual(m["pass_k"], 3 / 10)
        self.assertEqual(m["latency_p50"], 500)
        self.assertEqual(m["latency_p95"], 1000)
        self.assertEqual(m["input_tokens"], 100)
        self.assertEqual(m["output_tokens"], 10)

    def test_invalid_run_with_error_counts_once(self) -> None:
        r = grun(gcase("A", "positive", [DROP_S1]), None, error="x", invalid=True)
        self.assertAlmostEqual(metrics([r])["invalid_rate"], 1.0)

    def test_zero_denominators_are_none(self) -> None:
        m = metrics([grun(gcase("A", "positive", [DROP_S1]), DROP_S1)])
        for k in ("none_suppression", "over_call", "clarify_hit"):
            self.assertIsNone(m[k], k)
        self.assertEqual(m["unnecessary_clarify"], 0.0)
        self.assertEqual(m["param_error"], 0.0)
        only_clarify = metrics([grun(gcase("E", "clarify", [{"type": "clarify"}]), CLARIFY_AMBIG)])
        self.assertIsNone(only_clarify["unnecessary_clarify"])
        self.assertEqual(m["pair_accuracy"], {})
        empty = metrics([])
        self.assertIsNone(empty["macro_f1"])
        self.assertIsNone(empty["invalid_rate"])
        self.assertIsNone(empty["latency_p50"])

    def test_percentiles_nearest_rank(self) -> None:
        c = gcase("A", "positive", [DROP_S1])
        runs = [grun(c, DROP_S1, rep=i, latency_ms=v) for i, v in enumerate([40, 15, 50, 20, 35])]
        m = metrics(runs)
        self.assertEqual(m["latency_p50"], 35)
        self.assertEqual(m["latency_p95"], 50)

    def test_pass_k_fails_on_one_miss_in_five(self) -> None:
        good = gcase("G", "positive", [DROP_S1])
        flaky = gcase("F", "positive", [DROP_S1])
        runs = [grun(good, DROP_S1, rep=i) for i in range(5)]
        runs += [grun(flaky, DROP_S1 if i != 3 else NONE, rep=i) for i in range(5)]
        self.assertAlmostEqual(metrics(runs)["pass_k"], 1 / 2)

    def test_bootstrap_ci_is_deterministic(self) -> None:
        runs = []
        for i in range(8):
            c = gcase(f"c{i}", "positive", [DROP_S1], template=f"t{i}")
            runs.append(grun(c, DROP_S1 if i % 2 else NONE))
        first = bootstrap_ci(runs, n=200, seed=0)
        self.assertEqual(first, bootstrap_ci(runs, n=200, seed=0))
        lo, hi = first
        self.assertLessEqual(lo, hi)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)

    def test_bootstrap_ci_all_correct_is_one(self) -> None:
        runs = [
            grun(gcase(f"c{i}", "positive", [DROP_S1], template=f"t{i}"), DROP_S1)
            for i in range(4)
        ]
        self.assertEqual(bootstrap_ci(runs, n=50), (1.0, 1.0))
