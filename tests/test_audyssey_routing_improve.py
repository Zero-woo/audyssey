import copy
import importlib.resources
import json
import tempfile
import unittest
from pathlib import Path

import httpx2

from audyssey.contracts import Clarify, NoCommand
from audyssey.routing_eval import Case
from audyssey.routing_improve import improve, validate
from audyssey.tools.routing import Routed
from audyssey.settings import LLMEndpoint

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


FIXTURES = Path(__file__).resolve().parent.parent / "evals" / "routing" / "fixtures"
ENDPOINT = LLMEndpoint(
    api="openai", base_url="http://x/v1", model="imp", api_key="k",
    input="video", fps=1.0, max_frames=1, video_audio=False,
)


def cases(prefix: str, split: str, n: int = 3) -> list[Case]:
    return [
        Case.model_validate(
            {
                "id": f"{prefix}{i}", "fixture": "F1",
                "request": f"{prefix}-zxq{i}-wvu{i}", "category": "none",
                "template": f"{prefix}{i}", "expected": [], "split": split,
            }
        )
        for i in range(n)
    ]


def route_with(d: dict):
    when = d["commands"]["keep"]["when"]

    def route(request, job):
        # GOOD fixes dev only; train needs BEST, so round 2 still sees failures.
        good = when == "BEST" or (when == "GOOD" and request.startswith("dv"))
        decision = NoCommand() if good else Clarify(question="q", reason="other")
        return Routed(decision, None, 1.0, 1, 1)

    return route


def good_candidate(**keep) -> str:
    c = copy.deepcopy(CURRENT)
    c["commands"]["keep"]["when"] = "GOOD"
    c["commands"]["keep"].update(keep)
    return json.dumps({"commands": c["commands"]}, ensure_ascii=False)


class ImproveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bodies: list[dict] = []
        self.replies: list[str] = []

    def transport(self):
        def respond(request):
            self.bodies.append(json.loads(request.content))
            content = self.replies.pop(0)
            return httpx2.Response(200, json={
                "id": "t", "object": "chat.completion", "created": 0, "model": "imp",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": content}}],
            })
        return httpx2.MockTransport(respond)

    def run_improve(self, rounds=2, train=None, dev=None):
        return improve(
            route_with, "m", ENDPOINT,
            cases("tr", "train") if train is None else train,
            cases("dv", "dev") if dev is None else dev,
            FIXTURES, self.root / "cache", self.root / "out", rounds,
            transport=self.transport(),
        )

    def sent(self, i):
        return json.loads(self.bodies[i]["messages"][1]["content"])

    def test_dev_requests_never_reach_improver(self):
        self.replies = [good_candidate(), good_candidate()]
        self.run_improve()
        text = json.dumps(self.bodies, ensure_ascii=False)
        for c in cases("dv", "dev"):
            self.assertNotIn(c.request, text)
        self.assertIn("tr-zxq0-wvu0", text)
        body = self.bodies[0]
        self.assertEqual(body["temperature"], 1.0)
        self.assertTrue(body["response_format"]["json_schema"]["strict"])

    def test_invalid_candidate_is_skipped(self):
        self.replies = [good_candidate(when="가" * 401), "not json"]
        result = self.run_improve()
        self.assertEqual(result["rounds"][0]["verdict"], "rejected")
        self.assertEqual(result["rounds"][1]["verdict"], "rejected")
        self.assertFalse((self.root / "out/round-1/dev").exists())
        self.assertEqual(self.sent(1)["descriptions"], CURRENT["commands"])
        self.assertIsNone(result["best_round"])

    def test_adopted_candidate_becomes_base(self):
        self.replies = [good_candidate(), good_candidate(when="BEST")]
        result = self.run_improve()
        self.assertEqual(result["best_round"], 1)
        self.assertEqual(self.sent(1)["descriptions"]["keep"]["when"], "GOOD")
        self.assertEqual(result["rounds"][1]["verdict"], "not_adopted")
        out = self.root / "out"
        best = json.loads((out / "best.json").read_text())
        self.assertEqual(best["commands"]["keep"]["when"], "GOOD")
        self.assertEqual(json.loads((out / "summary.json").read_text())["best_round"], 1)

    def test_round_logs_written(self):
        self.replies = [good_candidate()]
        self.run_improve(rounds=1)
        r = self.root / "out/round-1"
        for name in ("candidate.json", "failures.jsonl", "verdict.json", "dev/summary.md"):
            self.assertTrue((r / name).exists(), name)
        verdict = json.loads((r / "verdict.json").read_text())
        self.assertEqual(verdict["verdict"], "adopted")
        self.assertTrue((self.root / "out/round-0/dev/summary.md").exists())

    def test_stops_when_train_has_no_failures(self):
        train = [
            c.model_copy(update={"category": "clarify", "expected": [{"type": "clarify"}]})
            for c in cases("tr", "train")
        ]
        result = self.run_improve(train=train)
        self.assertEqual(self.bodies, [])
        self.assertEqual(result["rounds"], [])
        self.assertIsNone(result["best_round"])
