import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from audyssey.api import create_app
from audyssey.settings import Settings


class SystemStatusTests(unittest.TestCase):
    """`/api/system` checks each server at the URL it was configured with."""

    def status(self, respond, **settings):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.calls = []

        def get(url, headers=None, timeout=None):
            self.calls.append((url, dict(headers or {})))
            return respond(url)

        app = create_app(Settings(work_dir=tmp.name, **settings))
        with patch("audyssey.api.httpx.get", side_effect=get):
            lanes = TestClient(app).get("/api/system").json()
        return {lane["id"]: lane for lane in lanes}

    def ok(self, url):
        return httpx.Response(200, request=httpx.Request("GET", url))

    def test_openrouter_checks_the_key_endpoint_with_the_key(self):
        lanes = self.status(
            self.ok,
            planner="real",
            planner_api="openrouter",
            planner_base_url="https://openrouter.ai/api/v1",
            planner_model="google/gemini-3.8-flash",
            planner_api_key="sk-or-test",
        )
        lane = lanes["llm:openrouter.ai"]
        self.assertEqual(lane["name"], "OpenRouter")
        self.assertEqual(lane["steps"], ["plan", "validate_plan"])
        self.assertTrue(lane["up"])
        self.assertEqual(
            self.calls,
            [("https://openrouter.ai/api/v1/key", {"Authorization": "Bearer sk-or-test"})],
        )

    def test_rejected_key_shows_the_server_as_down(self):
        lanes = self.status(
            lambda url: httpx.Response(401, request=httpx.Request("GET", url)),
            planner="real",
            planner_api="openrouter",
            planner_base_url="https://openrouter.ai/api/v1",
            planner_model="m",
            planner_api_key="sk-or-wrong",
        )
        self.assertFalse(lanes["llm:openrouter.ai"]["up"])

    def test_pod_vllm_keeps_https_and_the_v1_path(self):
        lanes = self.status(
            self.ok,
            planner="real",
            planner_base_url="https://pod-8000.proxy.runpod.net/v1/",
            planner_model="Qwen/VL",
        )
        self.assertTrue(lanes["llm:pod-8000.proxy.runpod.net"]["up"])
        self.assertEqual(self.calls, [("https://pod-8000.proxy.runpod.net/v1/models", {})])

    def test_missing_llm_url_is_down_without_a_request(self):
        lanes = self.status(self.ok, planner="real", planner_model="m")
        self.assertFalse(lanes["llm:"]["up"])
        self.assertEqual(self.calls, [])

    def test_unreachable_server_is_down(self):
        def refuse(url):
            raise httpx.ConnectError("refused")

        lanes = self.status(
            refuse,
            separator="remote",
            separator_url="https://pod-8700.proxy.runpod.net/",
        )
        self.assertFalse(lanes["tool:pod-8700.proxy.runpod.net"]["up"])
        # Tool servers keep their scheme and are checked at /health.
        self.assertEqual(self.calls, [("https://pod-8700.proxy.runpod.net/health", {})])
