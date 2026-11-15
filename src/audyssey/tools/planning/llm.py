import httpx2
from langsmith.wrappers import wrap_openai
from openai import DefaultHttpxClient, OpenAI

from audyssey.settings import Settings


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


def gemini_client(
    settings: Settings, transport: httpx2.BaseTransport | None = None
) -> httpx2.Client:
    """Client for Gemini's native REST API; POST models/<model>:generateContent."""
    if not settings.planner_base_url.strip():
        raise ValueError("AUDYSSEY_PLANNER_BASE_URL is required")
    return httpx2.Client(
        base_url=settings.planner_base_url,
        headers={"x-goog-api-key": settings.planner_api_key},
        # Same as the OpenAI SDK default.
        timeout=600,
        transport=_MaskKey(
            settings.planner_api_key, transport or httpx2.HTTPTransport()
        ),
    )


def chat_client(
    settings: Settings, transport: httpx2.BaseTransport | None = None
) -> OpenAI:
    """Return a traced client; callers pass settings.planner_model to create()."""
    if not settings.planner_base_url.strip():
        raise ValueError("AUDYSSEY_PLANNER_BASE_URL is required")
    return wrap_openai(
        OpenAI(
            base_url=settings.planner_base_url,
            api_key=settings.planner_api_key or "unused",
            http_client=DefaultHttpxClient(
                transport=_MaskKey(
                    settings.planner_api_key, transport or httpx2.HTTPTransport()
                )
            ),
        )
    )
