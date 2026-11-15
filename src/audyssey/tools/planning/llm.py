import httpx2
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


def gemini_client(
    endpoint: LLMEndpoint, transport: httpx2.BaseTransport | None = None
) -> httpx2.Client:
    """Client for Gemini's native REST API; POST models/<model>:generateContent."""
    _require_url(endpoint)
    return httpx2.Client(
        base_url=endpoint.base_url,
        headers={"x-goog-api-key": endpoint.api_key},
        # Same as the OpenAI SDK default.
        timeout=600,
        transport=_MaskKey(endpoint.api_key, transport or httpx2.HTTPTransport()),
    )


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
