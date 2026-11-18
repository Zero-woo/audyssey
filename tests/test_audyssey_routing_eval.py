import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError

from audyssey.contracts import Job
from audyssey.routing_eval import (
    Case,
    assign_splits,
    blank_labels,
    kappa,
    load_cases,
    load_fixture,
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
