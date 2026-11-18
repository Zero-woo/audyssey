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

    def test_router_format_setting(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(Settings().router_format, "tools")
        with patch.dict(os.environ, {"AUDYSSEY_ROUTER_FORMAT": "json_schema"}, clear=True):
            self.assertEqual(Settings().router_format, "json_schema")
        with self.assertRaises(ValueError):
            Settings.model_validate({"router_format": "xml"})

    def test_load_router_real_passes_format(self):
        with patch.object(real, "route") as route:
            for fmt in ("json_schema", "tools"):
                settings = Settings(
                    router="real",
                    router_format=fmt,
                    planner_base_url="http://test.invalid/v1",
                    planner_model="m",
                    planner_api_key="k",
                )
                load_router(settings)("dog 꺼줘", make_job())
                self.assertEqual(route.call_args.kwargs["fmt"], fmt)

    def test_load_router_real_passes_reasoning_effort(self):
        with patch.object(real, "route") as route:
            for effort in ("none", None):
                settings = Settings(
                    router="real",
                    router_reasoning_effort=effort,
                    planner_base_url="http://test.invalid/v1",
                    planner_model="m",
                    planner_api_key="k",
                )
                load_router(settings)("dog 꺼줘", make_job())
                self.assertEqual(route.call_args.kwargs["reasoning_effort"], effort)


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

    def route(self, request="dog 꺼줘", **kwargs):
        kwargs.setdefault("fmt", "json_schema")
        return real.route(
            request,
            make_job(),
            self.endpoint,
            transport=httpx2.MockTransport(self.respond),
            **kwargs,
        )

    def test_reasoning_effort_is_sent_only_when_set(self):
        self.route()
        self.assertNotIn("reasoning_effort", self.requests[0])
        self.route(reasoning_effort="none")
        self.assertEqual(self.requests[1]["reasoning_effort"], "none")

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
        self.assertEqual(data["version"], 3)
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


def _descriptions() -> dict:
    return json.loads(
        importlib.resources.files("audyssey.tools.routing")
        .joinpath("descriptions.json")
        .read_text(encoding="utf-8")
    )["commands"]


class ToolsRouterTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.calls = [("drop", {"source_id": "s1"})]
        self.content = None
        self.endpoint = Settings(
            planner_base_url="http://test.invalid/v1",
            planner_model="fake-model",
            planner_api_key="fake-key",
        ).router_endpoint()

    def respond(self, request):
        self.requests.append(json.loads(request.content))
        message = {
            "role": "assistant",
            "content": self.content,
            "tool_calls": [
                {
                    "id": f"c{i}",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": args if isinstance(args, str) else json.dumps(args),
                    },
                }
                for i, (name, args) in enumerate(self.calls)
            ]
            or None,
        }
        return httpx2.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": "fake-model",
                "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
                "choices": [{"index": 0, "finish_reason": "tool_calls", "message": message}],
            },
        )

    def route(self, request="dog 꺼줘", **kwargs):
        return real.route(
            request,
            make_job(),
            self.endpoint,
            transport=httpx2.MockTransport(self.respond),
            **kwargs,
        )

    def test_request_sends_ten_tools_and_requires_one(self):
        self.route()
        body = self.requests[0]
        commands = _descriptions()
        tools = body["tools"]
        self.assertEqual([t["type"] for t in tools], ["function"] * 10)
        self.assertEqual([t["function"]["name"] for t in tools], list(commands))
        for t in tools:
            name = t["function"]["name"]
            self.assertIn(commands[name]["when"], t["function"]["description"])
            self.assertIn("예: " + commands[name]["examples"][0], t["function"]["description"])
            self.assertNotIn("strict", t["function"])
            self.assertNotIn("type", t["function"]["parameters"].get("properties", {}))
        self.assertEqual(body["tool_choice"], "required")
        self.assertNotIn("response_format", body)
        self.assertEqual(body["temperature"], 0)

    def test_no_ref_in_parameters(self):
        self.route()
        for t in self.requests[0]["tools"]:
            text = json.dumps(t["function"]["parameters"])
            self.assertNotIn("$ref", text)
            self.assertNotIn("$defs", text)
        add_source = next(
            t for t in self.requests[0]["tools"] if t["function"]["name"] == "add_source"
        )
        self.assertIn("plan", add_source["function"]["parameters"]["properties"])

    def test_system_prompt_does_not_repeat_descriptions(self):
        self.route()
        system = self.requests[0]["messages"][0]["content"]
        self.assertNotIn(_descriptions()["set_gain"]["when"], system)
        self.assertIn("residual", system)

    def test_tool_calls_parse(self):
        for name, args, expected in [
            ("set_gain", {"source_id": "s1", "gain": 0.5}, SetGain(source_id="s1", gain=0.5)),
            ("clarify", {"question": "어느 소리?", "reason": "ambiguous_target"},
             Clarify(question="어느 소리?", reason="ambiguous_target")),
            ("none", {}, NoCommand()),
        ]:
            self.calls = [(name, args)]
            routed = self.route()
            self.assertEqual(routed.decision, expected)
            self.assertIsNone(routed.error)
            self.assertEqual((routed.input_tokens, routed.output_tokens), (7, 3))

    def test_called_tool_name_decides_the_type(self):
        self.calls = [("drop", {"type": "keep", "source_id": "s1"})]
        self.assertEqual(self.route().decision, Drop(source_id="s1"))

    def test_bad_responses_are_errors_without_retry(self):
        cases = {
            "text only": ([], "그냥 답변"),
            "two calls": ([("drop", {"source_id": "s1"}), ("none", {})], None),
            "bad json": ([("drop", "not json")], None),
            "non-object": ([("drop", "[1]")], None),
            "unknown name": ([("explode", {})], None),
            "invalid": ([("set_gain", {"source_id": "s1", "gain": 3})], None),
        }
        for label, (calls, content) in cases.items():
            self.requests.clear()
            self.calls, self.content = calls, content
            routed = self.route("secret request text")
            self.assertIsNone(routed.decision, label)
            assert routed.error is not None
            self.assertNotIn("secret", routed.error)
            self.assertEqual(len(self.requests), 1, label)

    def test_json_schema_mode_is_unchanged(self):
        self.content = '{"type": "drop", "source_id": "s1"}'
        self.calls = []
        routed = self.route(fmt="json_schema")
        self.assertEqual(routed.decision, Drop(source_id="s1"))
        body = self.requests[0]
        self.assertEqual(body["response_format"]["type"], "json_schema")
        self.assertNotIn("tools", body)
        self.assertNotIn("tool_choice", body)
        self.assertNotIn("지원하지 않는 요청은 none 또는", body["messages"][0]["content"])


class CacheKeyTests(unittest.TestCase):
    def test_cache_key_differs_between_formats(self):
        from pathlib import Path

        from audyssey.routing_eval import _cache_file

        root = Path("cache")
        self.assertNotEqual(
            _cache_file(root, "m", "c1", 0, "tools"),
            _cache_file(root, "m", "c1", 0, "json_schema"),
        )
        self.assertEqual(
            _cache_file(root, "m", "c1", 0, "tools"),
            _cache_file(root, "m", "c1", 0, "tools"),
        )
