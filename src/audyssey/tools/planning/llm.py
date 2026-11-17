import io
import time

import httpx2
from google import genai
from google.genai import types
from langsmith.wrappers import wrap_openai
from openai import DefaultHttpxClient, OpenAI

from audyssey.settings import LLMEndpoint


class _MaskKey(httpx2.BaseTransport):
    """Providers can echo the API key in error bodies; mask it, keep the rest."""

    def __init__(self, key: str, inner: httpx2.BaseTransport) -> None:
        self.key, self.inner = key.encode(), inner

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        response = self.inner.handle_request(request)
        if response.is_success or not self.key:
            return response
        body = response.read().replace(self.key, b"***")
        response.close()
        content_type = response.headers.get("content-type", "application/json")
        return httpx2.Response(
            response.status_code,
            headers={"content-type": content_type},
            content=body,
            request=request,
        )

    def close(self) -> None:
        self.inner.close()


def _require_url(endpoint: LLMEndpoint) -> None:
    if not endpoint.base_url.strip():
        raise ValueError(
            "AUDYSSEY_PLANNER_BASE_URL (or AUDYSSEY_VALIDATOR_BASE_URL) is required"
        )


def gemini_client(endpoint: LLMEndpoint) -> genai.Client:
    """Gemini SDK client; the SDK picks Google's endpoint, so base_url is unused."""
    return genai.Client(api_key=endpoint.api_key)


def gemini_upload(client: genai.Client, data: bytes, mime_type: str) -> types.File:
    """Upload through the Files API and wait until Gemini can read the file."""
    file = client.files.upload(file=io.BytesIO(data), config={"mime_type": mime_type})
    # ponytail: fixed 1 s poll capped at 2 min; short planner clips finish in seconds.
    for _ in range(120):
        if file.state != types.FileState.PROCESSING or not file.name:
            break
        time.sleep(1)
        file = client.files.get(name=file.name)
    if file.state != types.FileState.ACTIVE:
        raise RuntimeError(f"gemini file {file.name} is {file.state}")
    return file


def chat_client(
    endpoint: LLMEndpoint, transport: httpx2.BaseTransport | None = None
) -> OpenAI:
    """Return a traced client; callers pass endpoint.model to create()."""
    _require_url(endpoint)
    return wrap_openai(
        OpenAI(
            base_url=endpoint.base_url,
            api_key=endpoint.api_key or "unused",
            http_client=DefaultHttpxClient(
                transport=_MaskKey(
                    endpoint.api_key, transport or httpx2.HTTPTransport()
                )
            ),
        )
    )
