"""플래닝 담당 모듈의 기본 구현. 성능이 아니라 연결 확인용. 교체 가능."""

import base64
import json
import logging
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypeVar, cast

from langsmith import trace
from langsmith.run_helpers import tracing_context
from openai.types.chat import ChatCompletionContentPartParam, ChatCompletionMessageParam
from pydantic import TypeAdapter, ValidationError

from audyssey import media
from audyssey.contracts import Model, PlanIssue, SourcePlan, Span, VisualHint
from audyssey.settings import Settings
from audyssey.tools.planning import llm


class _Sources(Model):
    sources: list[object]


class _Issues(Model):
    issues: list[PlanIssue]


class _Span(Model):
    start: float
    end: float


class _Hint(Model):
    time: float
    box: tuple[float, float, float, float]
    description: str


_Response = TypeVar("_Response", bound=Model)


class _InvalidJSON(RuntimeError):
    pass


_RETRY = "Return valid JSON matching the schema."
# Gemini caps an inline request at 20 MB; the 512 px clip of a 30 s video is far below.
_MAX_INLINE_B64 = 19_000_000

_Usage = dict[str, int]
_Send = Callable[[bool], tuple[str | None, _Usage]]


def _clip(video: Path, settings: Settings, tmp: Path) -> str:
    clip = media.planner_clip(video, tmp / "planner.mp4", settings.planner_video_audio)
    data = base64.b64encode(clip.read_bytes()).decode("ascii")
    if len(data) > _MAX_INLINE_B64:
        # ponytail: inline only; upload through the Files API if clips outgrow 20 MB.
        raise RuntimeError("planner video is too large to send inline")
    return data


def _chat(video: Path, settings: Settings, system: str, text: str, tmp: Path) -> _Send:
    content: list[ChatCompletionContentPartParam] = [{"type": "text", "text": text}]
    extra: dict[str, object] = {}
    if settings.planner_input == "video":
        # vLLM's video_url part; not in the OpenAI SDK types.
        url = "data:video/mp4;base64," + _clip(video, settings, tmp)
        content.append(
            cast(
                ChatCompletionContentPartParam,
                {"type": "video_url", "video_url": {"url": url}},
            )
        )
        # num_frames=-1 lifts vLLM's 32-frame default so fps decides; needs
        # --trust-request-mm-kwargs on the server.
        extra["media_io_kwargs"] = {
            "video": {"fps": settings.planner_fps, "num_frames": -1}
        }
        if settings.planner_video_audio:
            extra["mm_processor_kwargs"] = {"use_audio_in_video": True}
    else:
        for time, path in media.extract_frames(video, settings.planner_frames, tmp):
            content.append({"type": "text", "text": f"Frame at {time:g} seconds"})
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                }
            )
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system},
        {"role": "user", "content": content},
    ]

    def send(retry: bool) -> tuple[str | None, _Usage]:
        if retry:
            messages.append({"role": "user", "content": _RETRY})
        with llm.chat_client(settings) as client:
            response = client.chat.completions.create(
                model=settings.planner_model,
                messages=messages,
                response_format={"type": "json_object"},
                extra_body=extra or None,
            )
        usage = response.usage
        return (
            response.choices[0].message.content if response.choices else None,
            {
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
            if usage
            else {},
        )

    return send


def _gemini(
    video: Path, settings: Settings, system: str, text: str, tmp: Path
) -> _Send:
    parts: list[dict[str, object]] = [
        {
            "inline_data": {
                "mime_type": "video/mp4",
                "data": _clip(video, settings, tmp),
            },
            "video_metadata": {"fps": settings.planner_fps},
        },
        {"text": text},
    ]
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    def send(retry: bool) -> tuple[str | None, _Usage]:
        if retry:
            parts.append({"text": _RETRY})
        with llm.gemini_client(settings) as client:
            response = client.post(
                f"models/{settings.planner_model}:generateContent", json=body
            )
            if not response.is_success:
                raise RuntimeError(
                    f"gemini request failed: {response.status_code} {response.text[:500]}"
                )
            data = response.json()
        candidates = data.get("candidates") or [{}]
        content = candidates[0].get("content") or {}
        raw = "".join(part.get("text", "") for part in content.get("parts") or [])
        meta = data.get("usageMetadata") or {}
        return raw or None, {
            "input_tokens": meta.get("promptTokenCount", 0),
            "output_tokens": meta.get("candidatesTokenCount", 0),
            "total_tokens": meta.get("totalTokenCount", 0),
        } if meta else {}

    return send


def _request(
    video: Path,
    settings: Settings,
    system: str,
    text: str,
    response_type: type[_Response],
) -> _Response:
    raw = None
    with TemporaryDirectory() as tmp:
        backend = _gemini if settings.planner_api == "gemini" else _chat
        send = backend(video, settings, system, text, Path(tmp))
        for attempt in range(2):
            # Record model/usage only: the SDK wrapper would also trace media bytes.
            with trace(
                "planner_completion",
                run_type="llm",
                inputs={"model": settings.planner_model},
                metadata={
                    "ls_model_name": settings.planner_model,
                    "ls_model_type": "chat",
                },
            ) as run:
                with tracing_context(enabled=False, parent=False):
                    raw, usage = send(attempt > 0)
                run.end(outputs={"usage_metadata": usage} if usage else {})
            try:
                data = json.loads(raw or "")
                if isinstance(data, list):
                    # Gemini sometimes drops the {"sources": [...]} wrapper.
                    (field,) = response_type.model_fields
                    data = {field: data}
                return response_type.model_validate(data)
            except (json.JSONDecodeError, ValidationError):
                continue
    excerpt = raw or ""
    if settings.planner_api_key:
        excerpt = excerpt.replace(settings.planner_api_key, "***")
    raise _InvalidJSON(f"planner returned invalid JSON: {excerpt[:500]}") from None


def _evidence(settings: Settings) -> str:
    if settings.planner_input == "frames":
        return (
            "Only frames are available, no audio; "
            "infer likely sources without claiming to hear them. "
        )
    if settings.planner_video_audio:
        return (
            "The video includes its audio track; list sounds you hear and "
            "visible things likely to make sound. "
        )
    return "The video is silent; infer likely sources without claiming to hear them. "


def _source(item: object, duration: float) -> SourcePlan:
    data = TypeAdapter(dict[str, object]).validate_python(item)
    if "spans" in data:
        if not isinstance(data["spans"], list):
            raise ValueError("spans must be a list")
        spans = []
        for value in data["spans"]:
            span = _Span.model_validate(value)
            start, end = (
                max(0, min(duration, span.start)),
                max(0, min(duration, span.end)),
            )
            if start < end:
                spans.append(Span(start=start, end=end))
        data["spans"] = spans
    if data.get("visual_hint") is not None:
        hint = _Hint.model_validate(data["visual_hint"])
        box = tuple(max(0, min(1, x)) for x in hint.box)
        data["visual_hint"] = (
            VisualHint(
                time=max(0, min(duration, hint.time)),
                box=(box[0], box[1], box[2], box[3]),
                description=hint.description,
            )
            if box[0] < box[2] and box[1] < box[3]
            else None
        )
    return SourcePlan.model_validate(data)


def plan(
    video: Path, audio: Path, duration: float, feedback: list[PlanIssue]
) -> list[SourcePlan]:
    settings = Settings()
    response = _request(
        video,
        settings,
        "You are an audio source planner. A source is one sound-producing entity. "
        "Do not split the same entity; use multiple spans for repeated sounds. "
        "Kinds: dialogue, sfx, music, ambience. "
        + _evidence(settings)
        + "Spans and hint times "
        "are seconds; boxes are [x0,y0,x1,y1] normalized to 0..1. "
        "Offscreen sources have visual_hint=null. Return JSON with a sources list. "
        "Each source follows this schema: "
        + json.dumps(SourcePlan.model_json_schema()),
        f"Video duration: {duration:g} seconds. Feedback: "
        + json.dumps([issue.model_dump() for issue in feedback]),
        _Sources,
    )
    sources = []
    for item in response.sources:
        try:
            sources.append(_source(item, duration))
        except ValueError:
            continue
    if not sources:
        raise RuntimeError("planner returned no valid sources")
    return sources


def validate_plan(video: Path, audio: Path, plans: list[SourcePlan]) -> list[PlanIssue]:
    settings = Settings()
    seen = "frames" if settings.planner_input == "frames" else "video"
    system = (
        f"Check the source list against the {seen}. Report only suspicious sources; "
        "do not report unsupported guesses about unheard audio. "
        "Return JSON with an issues list (empty when none). Each issue follows: "
        + json.dumps(PlanIssue.model_json_schema())
    )
    text = "Sources: " + json.dumps([source.model_dump() for source in plans])
    try:
        return _request(video, settings, system, text, _Issues).issues
    except _InvalidJSON:
        logging.getLogger(__name__).warning(
            "plan validator returned invalid JSON twice; proceeding without issues"
        )
        return []
