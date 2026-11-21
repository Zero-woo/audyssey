import copy
import importlib.resources
import json
import unittest

from audyssey.routing_improve import validate

CURRENT = json.loads(
    importlib.resources.files("audyssey.tools.routing")
    .joinpath("descriptions.json")
    .read_text(encoding="utf-8")
)
FAILED = ["개 짖는 소리 반으로 줄여줘"]


def candidate(**edit) -> dict:
    c = copy.deepcopy(CURRENT)
    for name, fields in edit.items():
        c["commands"][name].update(fields)
    return c


class ValidateTests(unittest.TestCase):
    def test_shipped_file_is_valid(self):
        self.assertEqual(validate(CURRENT, CURRENT, FAILED), [])

    def test_missing_command(self):
        c = copy.deepcopy(CURRENT)
        del c["commands"]["keep"]
        self.assertTrue(validate(c, CURRENT, []))

    def test_missing_field(self):
        c = copy.deepcopy(CURRENT)
        del c["commands"]["keep"]["when"]
        self.assertTrue(validate(c, CURRENT, []))

    def test_examples_string(self):
        self.assertTrue(validate(candidate(keep={"examples": "x"}), CURRENT, []))

    def test_length_limit(self):
        c = copy.deepcopy(CURRENT)
        k = c["commands"]["keep"]
        k["when"] = "가" * (400 - len(k["instead"]) - len(k["params"]) - sum(map(len, k["examples"])))
        self.assertEqual(validate(c, CURRENT, []), [])
        k["when"] += "가"
        self.assertTrue(validate(c, CURRENT, []))

    def test_overlap_six_chars(self):
        self.assertTrue(validate(candidate(keep={"when": "짖는 소리 반"}), CURRENT, FAILED))

    def test_overlap_five_chars_passes(self):
        self.assertEqual(validate(candidate(keep={"when": "짖는 소리"}), CURRENT, FAILED), [])

    def test_negative_in_instead(self):
        self.assertTrue(validate(candidate(keep={"instead": "drop은 고르지 마세요"}), CURRENT, []))
