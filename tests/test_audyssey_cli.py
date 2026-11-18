import unittest
from click import unstyle
from typer.testing import CliRunner
from audyssey.cli import app


class CliTests(unittest.TestCase):
    def test_cli_help(self):
        result = CliRunner().invoke(app, ["serve", "--help"], color=False)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--port", unstyle(result.output))

    def test_tool_server_help(self):
        result = CliRunner().invoke(app, ["tool-server", "--help"], color=False)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--tool", unstyle(result.output))
        self.assertIn("--impl", unstyle(result.output))

    def test_tool_server_refuses_public_host_without_token(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, AUDYSSEY_TOOL_TOKEN=""), patch("audyssey.cli.uvicorn.run") as run:
            result = CliRunner().invoke(app, ["tool-server", "--tool", "separation", "--host", "0.0.0.0"])
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("AUDYSSEY_TOOL_TOKEN is required when binding to a non-loopback host", unstyle(result.output))
        run.assert_not_called()

    def test_tool_server_accepts_loopback_or_authenticated_host(self):
        import os
        from unittest.mock import patch
        for host, token in [("127.0.0.1", ""), ("localhost", ""), ("::1", ""), ("0.0.0.0", "t")]:
            with self.subTest(host=host), patch.dict(os.environ, AUDYSSEY_TOOL_TOKEN=token), patch("audyssey.cli.uvicorn.run") as run:
                result = CliRunner().invoke(app, ["tool-server", "--tool", "filtering", "--host", host])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(run.call_args.kwargs["host"], host)

    def test_tool_server_accepts_repeated_tool_option(self):
        import os
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        with patch.dict(os.environ, AUDYSSEY_TOOL_TOKEN='t'), patch('audyssey.cli.uvicorn.run') as run:
            result = CliRunner().invoke(app, ['tool-server', '--tool', 'separation', '--tool', 'filtering', '--host', '0.0.0.0'])
        self.assertEqual(result.exit_code, 0, result.output)
        with TestClient(run.call_args.args[0]) as client:
            self.assertEqual(client.get('/health').json(), {'tools': ['separation', 'filtering'], 'impl': 'stub'})
            self.assertEqual({r.path for r in client.app.routes} & {'/separate', '/judge'}, {'/separate', '/judge'})

    def test_tool_server_requires_a_tool(self):
        result = CliRunner().invoke(app, ['tool-server'])
        self.assertEqual(result.exit_code, 2)

    def test_tool_server_rejects_unknown_tool(self):
        result = CliRunner().invoke(app, ['tool-server', '--tool', 'unknown'])
        self.assertEqual(result.exit_code, 2)

    def test_tool_server_accepts_grounding(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        with patch('audyssey.cli.uvicorn.run') as run:
            result = CliRunner().invoke(app, ['tool-server', '--tool', 'grounding'])
        self.assertEqual(result.exit_code, 0, result.output)
        with TestClient(run.call_args.args[0]) as client:
            self.assertEqual(client.get('/health').json()['tools'], ['grounding'])

    def test_tool_server_accepts_generation(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        with patch('audyssey.cli.uvicorn.run') as run:
            result = CliRunner().invoke(app, ['tool-server', '--tool', 'generation'])
        self.assertEqual(result.exit_code, 0, result.output)
        with TestClient(run.call_args.args[0]) as client:
            self.assertEqual(client.get('/health').json()['tools'], ['generation'])
            self.assertEqual({r.path for r in client.app.routes} & {'/generate', '/score'}, {'/generate', '/score'})


class EvalRoutingCliTests(unittest.TestCase):
    def setup(self, tmp):
        import shutil
        from pathlib import Path
        from audyssey.routing_eval import Case
        shutil.copytree(Path(__file__).resolve().parent.parent / "evals" / "routing" / "fixtures", Path(tmp) / "fixtures")
        cases = [Case.model_validate(dict(id=f"c{i}", fixture="F1", request="개 소리 꺼줘", category="none", template=f"t{i}", expected=[], split="dev")) for i in range(2)]
        (Path(tmp) / "cases.jsonl").write_text("".join(c.model_dump_json() + "\n" for c in cases))

    def invoke(self, tmp, *args, router=None):
        import os
        from pathlib import Path
        from unittest.mock import patch
        env = dict(AUDYSSEY_ROUTER_MODEL="m")
        fake = router or (lambda request, job: None)
        with patch.dict(os.environ, env), patch("audyssey.cli.load_router", return_value=fake):
            return CliRunner().invoke(app, ["eval-routing", "--cases", str(Path(tmp) / "cases.jsonl"), "--fixtures", str(Path(tmp) / "fixtures"), "--out", str(Path(tmp) / "out"), *args])

    def test_stub_run_writes_results_and_refuses_overwrite(self):
        import tempfile
        from pathlib import Path
        from audyssey.tools.routing import stub
        with tempfile.TemporaryDirectory() as tmp:
            self.setup(tmp)
            result = self.invoke(tmp, "--split", "dev", "--k", "2", router=stub.route)
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue((Path(tmp) / "out" / "summary.md").exists())
            again = self.invoke(tmp, "--split", "dev", "--k", "2", router=stub.route)
            self.assertEqual(again.exit_code, 1, again.output)

    def test_missing_split_exits_1(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.setup(tmp)
            result = self.invoke(tmp, "--split", "train")
            self.assertEqual(result.exit_code, 1, result.output)

    def test_real_router_needs_yes(self):
        import tempfile
        from pathlib import Path
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            self.setup(tmp)
            result = self.invoke(tmp, "--router", "real", "--split", "dev", "--k", "3", router=lambda r, j: calls.append(1))
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("6", result.output)
            self.assertIn("13800", result.output)
            self.assertEqual(calls, [])
            self.assertFalse((Path(tmp) / "out").exists())

    def test_test_split_is_logged_and_capped(self):
        import json
        import tempfile
        from pathlib import Path
        from audyssey.contracts import parse_decision
        from audyssey.tools.routing import Routed
        def router(r, j):
            return Routed(parse_decision({"type": "none"}), None, 1.0, 1, 1)
        with tempfile.TemporaryDirectory() as tmp:
            self.setup(tmp)
            path = Path(tmp) / "cases.jsonl"
            path.write_text(path.read_text().replace('"dev"', '"test"'))
            log = Path(tmp) / "test_opens.jsonl"
            result = self.invoke(tmp, "--router", "real", "--yes", "--split", "test", "--k", "1", router=router)
            self.assertEqual(result.exit_code, 0, result.output)
            entry = json.loads(log.read_text())
            self.assertEqual(entry["model"], "m")
            self.assertEqual(set(entry), {"date", "model", "git_sha", "out"})
            log.write_text('{"model": "m"}\n' * 3)
            (Path(tmp) / "out").rename(Path(tmp) / "out-old")
            result = self.invoke(tmp, "--router", "real", "--yes", "--split", "test", "--k", "1", router=router)
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertEqual(len(log.read_text().splitlines()), 3)

    def test_test_split_cap_is_per_model(self):
        import tempfile
        from pathlib import Path
        from audyssey.contracts import parse_decision
        from audyssey.tools.routing import Routed
        def router(r, j):
            return Routed(parse_decision({"type": "none"}), None, 1.0, 1, 1)
        with tempfile.TemporaryDirectory() as tmp:
            self.setup(tmp)
            path = Path(tmp) / "cases.jsonl"
            path.write_text(path.read_text().replace('"dev"', '"test"'))
            log = Path(tmp) / "test_opens.jsonl"
            log.write_text('{"model": "other"}\n' * 3)
            result = self.invoke(tmp, "--router", "real", "--yes", "--split", "test", "--k", "1", router=router)
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(len(log.read_text().splitlines()), 4)
            (Path(tmp) / "out").rename(Path(tmp) / "out-old")
            log.write_text('{"model": "m"}\n' * 3)
            result = self.invoke(tmp, "--router", "real", "--yes", "--split", "test", "--k", "1", router=router)
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("m", result.output)
            self.assertIn("3 opens", result.output)

    def test_crashed_test_run_is_not_counted(self):
        import tempfile
        from pathlib import Path
        calls = []
        def boom(request, job):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("network")
            from audyssey.contracts import parse_decision
            from audyssey.tools.routing import Routed
            return Routed(parse_decision({"type": "none"}), None, 1.0, 1, 1)
        with tempfile.TemporaryDirectory() as tmp:
            self.setup(tmp)
            path = Path(tmp) / "cases.jsonl"
            path.write_text(path.read_text().replace('"dev"', '"test"'))
            result = self.invoke(tmp, "--router", "real", "--yes", "--split", "test", "--k", "1", router=boom)
            self.assertNotEqual(result.exit_code, 0)
            self.assertFalse((Path(tmp) / "out").exists())
            self.assertFalse((Path(tmp) / "test_opens.jsonl").exists())

    def test_test_opens_are_appended_not_rewritten(self):
        import json
        import tempfile
        from pathlib import Path
        from audyssey.contracts import parse_decision
        from audyssey.tools.routing import Routed
        with tempfile.TemporaryDirectory() as tmp:
            self.setup(tmp)
            path = Path(tmp) / "cases.jsonl"
            path.write_text(path.read_text().replace('"dev"', '"test"'))
            log = Path(tmp) / "test_opens.jsonl"

            def router(r, j):
                # A concurrent run finishes while this one is routing.
                if not log.exists():
                    log.write_text('{"model": "m", "out": "other"}\n')
                return Routed(parse_decision({"type": "none"}), None, 1.0, 1, 1)

            result = self.invoke(tmp, "--router", "real", "--yes", "--split", "test", "--k", "1", router=router)
            self.assertEqual(result.exit_code, 0, result.output)
            lines = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual([e["out"] for e in lines][0], "other")
            self.assertEqual(len(lines), 2)

    def test_env_guard_is_ignored_and_effort_is_recorded(self):
        import json
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from audyssey.tools.routing import Routed
        from audyssey.contracts import parse_decision
        seen = []

        def fake_load(settings):
            seen.append(settings.router_guard)
            return lambda r, j: Routed(parse_decision({"type": "none"}), None, 1.0, 1, 1)

        with tempfile.TemporaryDirectory() as tmp:
            self.setup(tmp)
            env = dict(AUDYSSEY_ROUTER_MODEL="m", AUDYSSEY_ROUTER_GUARD="true", AUDYSSEY_ROUTER_REASONING_EFFORT="low")
            args = ["eval-routing", "--cases", str(Path(tmp) / "cases.jsonl"), "--fixtures", str(Path(tmp) / "fixtures"), "--out", str(Path(tmp) / "out"), "--router", "real", "--yes", "--split", "dev", "--k", "1"]
            with patch.dict(os.environ, env), patch("audyssey.cli.load_router", fake_load):
                result = CliRunner().invoke(app, args)
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(seen, [False])
            config = json.loads((Path(tmp) / "out" / "config.json").read_text())
            self.assertIs(config["guard"], False)
            self.assertEqual(config["reasoning_effort"], "low")

    def test_hybrid_without_decision_url_fails_fast(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            self.setup(tmp)
            result = self.invoke(tmp, "--router", "hybrid", "--yes", "--split", "dev")
            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("AUDYSSEY_ROUTER_DECISION_URL", result.output)
            self.assertFalse((Path(tmp) / "out").exists())
