import json
import unittest

from audyssey.contracts import (
    Clarify,
    Drop,
    Job,
    NoCommand,
    SetGain,
    Source,
    SourcePlan,
)
from audyssey.settings import Settings
from audyssey.tools.routing import load_router, summarize
from audyssey.tools.routing import stub


def make_job() -> Job:
    def source(id: str, name: str) -> Source:
        plan = SourcePlan(name=name, kind="sfx", description=f"secret {name} text")
        return Source(id=id, plan=plan, gain=0.8)

    return Job(
        id="j",
        video_path="v.mp4",
        sources=[source("s1", "dog"), source("s2", "car")],
    )


class RoutingTests(unittest.TestCase):
    def test_summarize_has_residual_and_no_descriptions(self):
        summary = summarize(make_job())
        self.assertEqual(summary["residual"]["id"], "residual")
        self.assertEqual(summary["sources"][0]["name"], "dog")
        self.assertNotIn("secret", json.dumps(summary))

    def test_stub_drop_names_the_source(self):
        routed = stub.route("dog 꺼줘", make_job())
        self.assertEqual(routed.decision, Drop(source_id="s1"))
        self.assertIsNone(routed.error)

    def test_stub_gain_goes_down(self):
        decision = stub.route("dog 소리 줄여줘", make_job()).decision
        assert isinstance(decision, SetGain)
        self.assertEqual(decision.source_id, "s1")
        self.assertLess(decision.gain, 0.8)

    def test_stub_question_is_no_command(self):
        self.assertEqual(
            stub.route("이 영상 몇 분이야?", make_job()).decision, NoCommand()
        )

    def test_stub_ambiguous_or_missing_target_clarifies(self):
        for request in ["dog car 꺼줘", "bird 꺼줘"]:
            decision = stub.route(request, make_job()).decision
            assert isinstance(decision, Clarify)
            self.assertEqual(decision.reason, "ambiguous_target")

    def test_load_router(self):
        self.assertIs(load_router(Settings(router="stub")), stub.route)
        with self.assertRaises(ValueError):
            load_router(Settings(router="real"))
