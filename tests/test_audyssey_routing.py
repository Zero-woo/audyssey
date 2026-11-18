import importlib.resources
import json
import os
import unittest
from unittest.mock import patch

import httpx2
from langsmith.run_helpers import get_tracing_context

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
from audyssey.tools.routing import real, stub


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

    def test_load_router_real_binds_endpoint(self):
        settings = Settings(
            router="real",
            planner_base_url="http://test.invalid/v1",
            planner_model="m",
            planner_api_key="k",
        )
        with patch.object(real, "route") as route:
            load_router(settings)("dog 꺼줘", make_job())
        route.assert_called_once()
        self.assertEqual(route.call_args.args[2], settings.router_endpoint())


class RealRouterTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.tracing = []
        self.content = '{"type": "drop", "source_id": "s1"}'
        env = patch.dict(
            os.environ,
            {"LANGSMITH_TRACING": "true", "LANGSMITH_API_KEY": "fake"},
            clear=True,
        )
        env.start()
        self.addCleanup(env.stop)
        self.endpoint = Settings(
            planner_base_url="http://test.invalid/v1",
            planner_model="fake-model",
            planner_api_key="fake-key",
        ).router_endpoint()

    def respond(self, request):
        self.requests.append(json.loads(request.content))
        self.tracing.append(get_tracing_context()["enabled"])
        return httpx2.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": "fake-model",
                "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": self.content},
                    }
                ],
            },
        )

    def route(self, request="dog 꺼줘"):
        return real.route(
            request,
            make_job(),
            self.endpoint,
            transport=httpx2.MockTransport(self.respond),
        )

    def test_valid_response(self):
        routed = self.route()
        self.assertEqual(routed.decision, Drop(source_id="s1"))
        self.assertIsNone(routed.error)
        self.assertEqual((routed.input_tokens, routed.output_tokens), (7, 3))
        self.assertGreaterEqual(routed.latency_ms, 0)

    def test_request_body(self):
        self.route("secret request text")
        body = self.requests[0]
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["model"], "fake-model")
        self.assertEqual(body["response_format"]["type"], "json_schema")
        self.assertEqual(body["response_format"]["json_schema"]["schema"], real.DECISION_SCHEMA)
        user = json.loads(body["messages"][1]["content"])
        self.assertEqual(user["request"], "secret request text")
        self.assertEqual(user["job"], summarize(make_job()))

    def test_schema_violation_is_an_error_without_retry(self):
        for content in [
            '{"type": "set_gain", "source_id": "s1", "gain": 3}',
            "not json",
            "[1]",
        ]:
            self.requests.clear()
            self.content = content
            routed = self.route("secret request text")
            self.assertIsNone(routed.decision)
            assert routed.error is not None
            self.assertNotIn("secret", routed.error)
            self.assertEqual(len(self.requests), 1)

    def test_empty_choices_is_an_error_without_retry(self):
        def respond(request):
            self.requests.append(json.loads(request.content))
            return httpx2.Response(200, json={
                "id": "test", "object": "chat.completion", "created": 0,
                "model": "fake-model", "choices": [],
            })

        routed = real.route(
            "secret request text", make_job(), self.endpoint,
            transport=httpx2.MockTransport(respond),
        )
        self.assertIsNone(routed.decision)
        assert routed.error is not None
        self.assertNotIn("secret", routed.error)
        self.assertEqual(len(self.requests), 1)

    def test_tracing_is_disabled_during_call(self):
        self.route()
        self.assertEqual(self.tracing, [False])

    def test_descriptions_file(self):
        data = json.loads(
            importlib.resources.files("audyssey.tools.routing")
            .joinpath("descriptions.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(data["version"], 2)
        self.assertNotIn("제한", data["commands"]["set_gain"]["params"])
        commands = data["commands"]
        self.assertEqual(len(commands), 10)
        self.assertEqual(
            set(commands),
            {"keep", "drop", "set_gain", "set_pitch", "reseparate", "generate",
             "add_source", "render", "clarify", "none"},
        )
        for name, entry in commands.items():
            self.assertEqual(set(entry), {"when", "instead", "params", "examples"}, name)
            text = [entry["when"], entry["instead"], entry["params"], *entry["examples"]]
            self.assertLessEqual(sum(map(len, text)), 400, name)
            self.assertNotIn("하지 마", entry["instead"], name)
