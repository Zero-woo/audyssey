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
    Generate,
    Job,
    NoCommand,
    Render,
    Reseparate,
    SetGain,
    SetPitch,
    Source,
    SourcePlan,
)
from audyssey.settings import Settings
from audyssey.tools.routing import Routed, guard, load_router, summarize
from audyssey.tools.routing import hybrid, model_name, real, stub


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

    def test_real_route_uses_descriptions_override(self):
        d = {"commands": {k: dict(v) for k, v in _descriptions().items()}}
        d["commands"]["drop"]["when"] = "OVERRIDE-WHEN-SENTENCE"
        self.route(descriptions=d)
        tools = {t["function"]["name"]: t for t in self.requests[0]["tools"]}
        self.assertIn("OVERRIDE-WHEN-SENTENCE", tools["drop"]["function"]["description"])

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

    def test_cache_key_differs_between_reasoning_efforts(self):
        from pathlib import Path

        from audyssey.routing_eval import _cache_file

        root = Path("cache")
        keys = {
            _cache_file(root, "m", "c1", 0, "tools", effort)
            for effort in (None, "none", "low")
        }
        self.assertEqual(len(keys), 3)

    def test_cache_key_unchanged_without_salt(self):
        import hashlib
        from pathlib import Path

        from audyssey.routing_eval import _cache_file, _descriptions

        key = json.dumps(["m", "tools", None, _descriptions()[0], "c1", 0])
        want = Path("cache") / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
        self.assertEqual(_cache_file(Path("cache"), "m", "c1", 0, "tools"), want)
        self.assertEqual(_cache_file(Path("cache"), "m", "c1", 0, "tools", salt=""), want)

    def test_cache_key_follows_descriptions(self):
        from pathlib import Path

        from audyssey.routing_eval import _cache_file

        a = {"version": 1, "commands": {"keep": {"when": "a"}}}
        b = {"version": 1, "commands": {"keep": {"when": "b"}}}
        p = Path("cache")
        paths = {
            _cache_file(p, "m", "c1", 0, "tools", descriptions=d) for d in (None, a, b)
        }
        self.assertEqual(len(paths), 3)
        self.assertEqual(
            _cache_file(p, "m", "c1", 0, "tools", descriptions=a),
            _cache_file(p, "m", "c1", 0, "tools", descriptions=dict(a)),
        )

    def test_salt_changes_cache_file(self):
        from pathlib import Path

        from audyssey.routing_eval import _cache_file
        from audyssey.tools.routing import cache_salt

        root = Path("cache")
        self.assertNotEqual(
            _cache_file(root, "m", "c1", 0, "tools", salt="a"),
            _cache_file(root, "m", "c1", 0, "tools", salt="b"),
        )
        self.assertEqual(cache_salt("real"), "")
        self.assertRegex(cache_salt("hybrid"), r"^[0-9a-f]{12}$")

def routed(decision) -> Routed:
    return Routed(decision, None, 7.0, 11, 3)


class GuardTests(unittest.TestCase):
    def dialogue_job(self, silent: bool = False) -> Job:
        plan = SourcePlan(name="talk", kind="dialogue", description="d")
        return Job(
            id="j",
            video_path="v.mp4",
            silent=silent,
            sources=[Source(id="s1", plan=plan, gain=0.8)],
        )

    def assert_clarified(self, out: Routed, reason: str, question: str):
        self.assertEqual(out.decision, Clarify(question=question, reason=reason))
        self.assertTrue(out.guarded)
        self.assertEqual((out.latency_ms, out.input_tokens, out.output_tokens), (7.0, 11, 3))

    def test_dialogue_generate_is_unsupported(self):
        out = guard(self.dialogue_job(), routed(Generate(source_id="s1")))
        self.assert_clarified(out, "unsupported", "대사는 새로 만들 수 없어요.")

    def test_silent_video_reseparate_is_unsupported(self):
        out = guard(make_job().model_copy(update={"silent": True}), routed(Reseparate(source_id="s1")))
        self.assert_clarified(
            out, "unsupported", "생성한 소리나 소리가 없는 영상은 다시 분리할 수 없어요."
        )

    def test_unknown_source_is_ambiguous_target(self):
        out = guard(make_job(), routed(Drop(source_id="nope")))
        self.assert_clarified(out, "ambiguous_target", "어느 소리를 말씀하시나요?")

    def test_residual_messages(self):
        job = make_job()
        for decision, text in [
            (Generate(source_id="residual"), "나머지 소리는 새로 만들 수 없어요."),
            (SetPitch(source_id="residual", semitones=1), "나머지 소리는 음높이를 바꿀 수 없어요."),
            (Reseparate(source_id="residual"), "나머지 소리는 다시 분리할 수 없어요."),
        ]:
            self.assert_clarified(guard(job, routed(decision)), "unsupported", text)

    def test_unchanged_answers(self):
        for decision in [
            SetGain(source_id="s1", gain=0.5),
            Clarify(question="q", reason="other"),
            NoCommand(),
            None,
        ]:
            original = routed(decision)
            out = guard(make_job(), original)
            self.assertEqual(out, original)
            self.assertFalse(out.guarded)

    def test_load_router_wraps_only_when_guard_on(self):
        def bad(request: str, job: Job) -> Routed:
            return routed(Drop(source_id="nope"))

        with patch.object(stub, "route", bad):
            self.assertIs(load_router(Settings(router="stub")), bad)
            out = load_router(Settings(router="stub", router_guard=True))("x", make_job())
        assert isinstance(out.decision, Clarify)
        self.assertTrue(out.guarded)



class HybridTests(unittest.TestCase):
    def setUp(self):
        self.decision_requests = []
        self.llm_requests = []
        self.decision_status = 200
        self.decision_body = None
        self.choice = "set_gain"
        self.target = "s1"
        self.noul = 0.3
        self.composite = 0.0
        self.probabilities = {}
        self.calls = [("set_gain", {"source_id": "s1", "gain": 0.5})]
        self.endpoint = Settings(
            planner_base_url="http://test.invalid/v1",
            planner_model="fake-model",
            planner_api_key="fake-key",
        ).router_endpoint()

    def decide(self, request):
        self.decision_requests.append(json.loads(request.content))
        if self.decision_body is not None:
            return httpx2.Response(self.decision_status, content=self.decision_body)
        answer = {"type": "choice", "confidence": 1.0, "probabilities": {}}
        return httpx2.Response(
            self.decision_status,
            json={
                "answers": {
                    "decision": {**answer, "choice": self.choice},
                    "target": {
                        **answer,
                        "choice": self.target,
                        "probabilities": self.probabilities,
                    },
                    "residual_stem": {"type": "noul", "noul": self.noul},
                    "composite": {"type": "noul", "noul": self.composite},
                },
                "usage": {"input_tokens": 100},
            },
        )

    def llm(self, request):
        self.llm_requests.append(json.loads(request.content))
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"c{i}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args)},
                }
                for i, (name, args) in enumerate(self.calls)
            ],
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

    def route(self, escape=False, **kwargs):
        return hybrid.route(
            "dog 키워줘",
            make_job(),
            "http://decision.invalid",
            self.endpoint,
            escape=escape,
            decision_transport=httpx2.MockTransport(self.decide),
            llm_transport=httpx2.MockTransport(self.llm),
            **kwargs,
        )

    def test_hybrid_questions_use_descriptions_override(self):
        d = {"commands": {k: dict(v) for k, v in _descriptions().items()}}
        d["commands"]["drop"]["when"] = "OVERRIDE-WHEN-SENTENCE"
        self.assertIn(
            "OVERRIDE-WHEN-SENTENCE",
            hybrid._questions(make_job(), d)["decision"]["criteria"]["drop"],
        )

    def test_route_sends_descriptions_override_to_decision_server(self):
        d = {"commands": {k: dict(v) for k, v in _descriptions().items()}}
        d["commands"]["drop"]["when"] = "OVERRIDE-WHEN-SENTENCE"
        self.route(descriptions=d)
        criteria = self.decision_requests[0]["questions"]["decision"]["criteria"]
        self.assertIn("OVERRIDE-WHEN-SENTENCE", criteria["drop"])

    def test_stage_one_only_commands_skip_the_llm(self):
        cases = [
            ("none", "s1", 0.3, NoCommand()),
            (
                "clarify_missing_value",
                "s1",
                0.3,
                Clarify(reason="missing_value", question="얼마나 바꿀까요?"),
            ),
            ("drop", "s2", 0.3, Drop(source_id="s2")),
            ("render", "s1", 0.7, Render(include_residual_stem=True)),
            ("render", "s1", 0.3, Render(include_residual_stem=False)),
        ]
        for choice, target, noul, expected in cases:
            with self.subTest(choice=choice, noul=noul):
                self.choice, self.target, self.noul = choice, target, noul
                routed = self.route()
                self.assertEqual(routed.decision, expected)
                self.assertIsNone(routed.error)
        self.assertEqual(self.llm_requests, [])

    def test_decision_request_wire_format(self):
        self.choice = "none"
        self.route()
        body = self.decision_requests[0]
        self.assertEqual(body["state"]["request"], "dog 키워줘")
        self.assertEqual(body["state"]["job"], summarize(make_job()))
        questions = body["questions"]
        self.assertEqual(questions["decision"]["type"], "choice")
        self.assertEqual(len(questions["decision"]["criteria"]), 14)
        self.assertEqual(
            questions["decision"]["criteria"]["clarify_missing_value"],
            "되물어야 함: 크기나 음높이를 바꾸려는데 양이 없거나 \"조금\"처럼 모호함",
        )
        self.assertEqual(
            questions["target"]["criteria"],
            {
                "s1": "dog (sfx, 켜짐)",
                "s2": "car (sfx, 켜짐)",
                "residual": "residual: 분리되지 않고 남은 나머지 소리",
            },
        )
        self.assertEqual(questions["residual_stem"]["type"], "noul")
        self.assertEqual(
            set(questions), {"decision", "target", "residual_stem", "composite"}
        )
        self.assertEqual(
            questions["composite"],
            {
                "type": "noul",
                "instructions": "요청(request)에 서로 다른 편집이 둘 이상 들어 있나요?",
            },
        )

    def test_set_gain_fills_value_with_one_tool(self):
        routed = self.route()
        self.assertEqual(routed.decision, SetGain(source_id="s1", gain=0.5))
        body = self.llm_requests[0]
        self.assertEqual([t["function"]["name"] for t in body["tools"]], ["set_gain"])
        props = body["tools"][0]["function"]["parameters"]["properties"]
        self.assertEqual(props["source_id"], {"enum": ["s1"]})
        self.assertEqual(body["tool_choice"], "required")
        self.assertEqual(body["temperature"], 0)
        user = json.loads(body["messages"][1]["content"])
        self.assertEqual(user["decided"], {"type": "set_gain", "source_id": "s1"})
        self.assertEqual(user["request"], "dog 키워줘")

    def test_escape_adds_clarify_tool(self):
        self.calls = [("clarify", {"reason": "missing_value", "question": "얼마나요?"})]
        routed = self.route(escape=True)
        self.assertEqual(
            routed.decision, Clarify(reason="missing_value", question="얼마나요?")
        )
        tools = self.llm_requests[0]["tools"]
        self.assertEqual([t["function"]["name"] for t in tools], ["set_gain", "clarify"])
        reason = tools[1]["function"]["parameters"]["properties"]["reason"]
        self.assertEqual(reason["enum"], ["missing_value"])
        self.assertIn("clarify", self.llm_requests[0]["messages"][0]["content"])

    def test_clarify_not_offered_without_escape(self):
        self.calls = [("clarify", {"reason": "missing_value", "question": "q"})]
        routed = self.route()
        self.assertIsNone(routed.decision)
        assert routed.error is not None

    def test_wrong_type_is_an_error(self):
        self.calls = [("drop", {"source_id": "s1"})]
        routed = self.route()
        self.assertIsNone(routed.decision)
        assert routed.error is not None

    def test_decision_server_failure_is_an_error_without_retry(self):
        for status, body in [(200, b"not json"), (200, b"{}")]:
            with self.subTest(status=status, body=body):
                self.decision_requests.clear()
                self.decision_status, self.decision_body = status, body
                routed = self.route()
                self.assertIsNone(routed.decision)
                self.assertEqual(routed.error, "decision server failed")
                self.assertEqual(len(self.decision_requests), 1)
        self.assertEqual(self.llm_requests, [])

    def test_transport_failure_propagates(self):
        self.decision_status, self.decision_body = 500, b"boom"
        with self.assertRaises(httpx2.HTTPError):
            self.route()

    def test_non_string_choice_is_an_error(self):
        for choice, target in [(["keep"], "s1"), ("keep", 3)]:
            with self.subTest(choice=choice, target=target):
                self.choice, self.target = choice, target
                routed = self.route()
                self.assertIsNone(routed.decision)
                self.assertEqual(routed.error, "decision server failed")

    def test_hybrid_keeps_raw_answers(self):
        self.choice = "none"
        routed = self.route()
        answer = {"type": "choice", "confidence": 1.0, "probabilities": {}}
        self.assertEqual(
            routed.raw,
            {
                "decision": {**answer, "choice": "none"},
                "target": {**answer, "choice": "s1"},
                "residual_stem": {"type": "noul", "noul": 0.3},
                "composite": {"type": "noul", "noul": 0.0},
            },
        )

    def test_override_table(self):
        two = {"s1": 0.9, "s2": 0.1}
        tie = {"s1": 0.5, "s2": 0.5}
        cases = [
            ("set_gain", 0.9, two, 0.5, None, "composite"),
            ("set_gain", 0.4, two, 0.5, None, None),
            ("none", 0.9, {}, 0.5, None, None),
            ("clarify_missing_value", 0.9, {}, 0.5, None, None),
            ("drop", 0.1, {"s1": 0.48, "s2": 0.45, "s3": 0.07}, None, 0.2,
             "ambiguous_target"),
            ("drop", 0.1, {"s1": 0.8, "s2": 0.1}, None, 0.2, None),
            ("render", 0.1, tie, None, 0.2, None),
            ("add_source", 0.1, tie, None, 0.2, None),
            ("drop", 0.9, tie, 0.5, 0.2, "composite"),
            ("drop", 0.9, tie, None, None, None),
        ]
        for kind, noul, probs, cmin, margin, expected in cases:
            with self.subTest(kind=kind, noul=noul, cmin=cmin, margin=margin):
                answers = {
                    "composite": {"noul": noul},
                    "target": {"probabilities": probs},
                }
                self.assertEqual(hybrid.override(kind, answers, cmin, margin), expected)

    def test_override_turns_into_clarify_without_llm(self):
        self.composite = 0.9
        routed = self.route(composite_min=0.5)
        self.assertEqual(
            routed.decision,
            Clarify(reason="composite", question=hybrid.QUESTIONS["composite"]),
        )
        self.assertEqual(self.llm_requests, [])
        self.assertIsNotNone(routed.raw)

    def test_rules_off_by_default(self):
        self.composite = 0.99
        self.probabilities = {"s1": 0.5, "s2": 0.5}
        routed = self.route()
        self.assertEqual(routed.decision, SetGain(source_id="s1", gain=0.5))
        self.assertEqual(len(self.llm_requests), 1)

    def test_latency_and_tokens_are_summed(self):
        routed = self.route()
        self.assertEqual((routed.input_tokens, routed.output_tokens), (107, 3))
        self.assertGreater(routed.latency_ms, 0)
        self.choice = "none"
        routed = self.route()
        self.assertEqual((routed.input_tokens, routed.output_tokens), (100, 0))

    def test_model_name_separates_escape(self):
        base = {"router": "hybrid", "router_decision_url": "http://d", "router_model": "m"}
        off = model_name(Settings(**base))
        on = model_name(Settings(**base, router_hybrid_escape=True))
        self.assertEqual(off, "hybrid[h2o-lightning-4b+m]")
        self.assertEqual(on, "hybrid[h2o-lightning-4b+m+escape]")
        self.assertEqual(model_name(Settings(router="stub")), "stub")
        from pathlib import Path

        from audyssey.routing_eval import _cache_file

        self.assertNotEqual(
            _cache_file(Path("c"), off, "c1", 0, "tools"),
            _cache_file(Path("c"), on, "c1", 0, "tools"),
        )

    def test_load_router_hybrid(self):
        settings = Settings(
            router="hybrid",
            router_decision_url="http://decision.invalid",
            planner_base_url="http://test.invalid/v1",
        )
        with patch.object(hybrid, "route") as route:
            load_router(settings)("dog 꺼줘", make_job())
        self.assertEqual(route.call_args.args[3], settings.router_endpoint())
        self.assertEqual(route.call_args.args[1], make_job())
