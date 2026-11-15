"""플래닝 담당 모듈의 기본 구현. 성능이 아니라 연결 확인용. 교체 가능."""

import base64
import json
import logging
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal, TypeVar, cast

from langsmith import trace
from langsmith.run_helpers import tracing_context
from openai.types.chat import ChatCompletionContentPartParam, ChatCompletionMessageParam
from pydantic import TypeAdapter, ValidationError

from audyssey import media
from audyssey.contracts import Model, PlanIssue, SourcePlan, Span, VisualHint
from audyssey.settings import LLMEndpoint, Settings
from audyssey.tools.planning import llm


class _Sources(Model):
    sources: list[object]


class _Check(Model):
    present: bool
    reason: str = ""


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
# Gemini caps an inline request at 20 MB; 512 px clips of a 30 s video are far below.
_MAX_INLINE_B64 = 19_000_000

# Provider-neutral request media: labels, base64 JPEG frames, base64 mp4 clips.
_Part = tuple[Literal["text", "image", "video"], str]
_Usage = dict[str, int]
_Send = Callable[[bool], tuple[str | None, _Usage]]


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _media(
    video: Path, endpoint: LLMEndpoint, windows: list[tuple[float, float]], tmp: Path
) -> list[_Part]:
    """Frames sampled at endpoint.fps, or one clip per time window."""
    parts: list[_Part] = []
    left = endpoint.max_frames
    for i, (start, end) in enumerate(windows):
        if endpoint.input == "video":
            clip = media.planner_clip(
                video, tmp / f"clip-{i}.mp4", endpoint.video_audio, start, end
            )
            parts += [
                ("text", f"Video from {start:g} to {end:g} seconds"),
                ("video", _b64(clip)),
            ]
            continue
        if left == 0:
            # ponytail: frames past max_frames are dropped, later windows unseen.
            break
        count = max(1, min(round((end - start) * endpoint.fps), left))
        left -= count
        for time, path in media.extract_frames(
            video, count, tmp / f"frames-{i}", start, end
        ):
            parts += [("text", f"Frame at {time:g} seconds"), ("image", _b64(path))]
    if sum(len(value) for kind, value in parts if kind == "video") > _MAX_INLINE_B64:
        # ponytail: inline only; upload through the Files API if clips outgrow 20 MB.
        raise RuntimeError("planner video is too large to send inline")
    return parts


def _chat(endpoint: LLMEndpoint, system: str, text: str, parts: list[_Part]) -> _Send:
    content: list[ChatCompletionContentPartParam] = [{"type": "text", "text": text}]
    for kind, value in parts:
        if kind == "text":
            content.append({"type": "text", "text": value})
        elif kind == "image":
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{value}"},
                }
            )
        else:
            # vLLM's video_url part; not in the OpenAI SDK types.
            content.append(
                cast(
                    ChatCompletionContentPartParam,
                    {
                        "type": "video_url",
                        "video_url": {"url": f"data:video/mp4;base64,{value}"},
                    },
                )
            )
    extra: dict[str, object] = {}
    if any(kind == "video" for kind, _ in parts):
        # num_frames=-1 lifts vLLM's 32-frame default so fps decides; needs
        # --trust-request-mm-kwargs on the server.
        extra["media_io_kwargs"] = {"video": {"fps": endpoint.fps, "num_frames": -1}}
        if endpoint.video_audio:
            extra["mm_processor_kwargs"] = {"use_audio_in_video": True}
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system},
        {"role": "user", "content": content},
    ]

    def send(retry: bool) -> tuple[str | None, _Usage]:
        if retry:
            messages.append({"role": "user", "content": _RETRY})
        with llm.chat_client(endpoint) as client:
            response = client.chat.completions.create(
                model=endpoint.model,
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


def _gemini(endpoint: LLMEndpoint, system: str, text: str, parts: list[_Part]) -> _Send:
    contents: list[dict[str, object]] = []
    for kind, value in parts:
        if kind == "text":
            contents.append({"text": value})
        elif kind == "image":
            contents.append({"inline_data": {"mime_type": "image/jpeg", "data": value}})
        else:
            contents.append(
                {
                    "inline_data": {"mime_type": "video/mp4", "data": value},
                    "video_metadata": {"fps": endpoint.fps},
                }
            )
    contents.append({"text": text})
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": contents}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    def send(retry: bool) -> tuple[str | None, _Usage]:
        if retry:
            contents.append({"text": _RETRY})
        with llm.gemini_client(endpoint) as client:
            response = client.post(
                f"models/{endpoint.model}:generateContent", json=body
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
    endpoint: LLMEndpoint,
    system: str,
    text: str,
    parts: list[_Part],
    response_type: type[_Response],
) -> _Response:
    backend = _gemini if endpoint.api == "gemini" else _chat
    send = backend(endpoint, system, text, parts)
    raw = None
    for attempt in range(2):
        # Record model/usage only: the SDK wrapper would also trace media bytes.
        with trace(
            "planner_completion",
            run_type="llm",
            inputs={"model": endpoint.model},
            metadata={"ls_model_name": endpoint.model, "ls_model_type": "chat"},
        ) as run:
            with tracing_context(enabled=False, parent=False):
                raw, usage = send(attempt > 0)
            run.end(outputs={"usage_metadata": usage} if usage else {})
        try:
            data = json.loads(raw or "")
            if isinstance(data, list) and len(response_type.model_fields) == 1:
                # Gemini sometimes drops the {"sources": [...]} wrapper.
                (field,) = response_type.model_fields
                data = {field: data}
            return response_type.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            continue
    excerpt = raw or ""
    if endpoint.api_key:
        excerpt = excerpt.replace(endpoint.api_key, "***")
    raise _InvalidJSON(f"planner returned invalid JSON: {excerpt[:500]}") from None


def _hears(endpoint: LLMEndpoint) -> bool:
    return endpoint.input == "video" and endpoint.video_audio


def _evidence(endpoint: LLMEndpoint) -> str:
    if endpoint.input == "frames":
        return (
            "Only frames are available, no audio; "
            "infer likely sources without claiming to hear them. "
        )
    if _hears(endpoint):
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
    endpoint = Settings().planner_endpoint()
    with TemporaryDirectory() as tmp:
        parts = _media(video, endpoint, [(0.0, duration)], Path(tmp))
    response = _request(
        endpoint,
        "You are an audio source planner. A source is one sound-producing entity. "
        "Do not split the same entity; use multiple spans for repeated sounds. "
        "Kinds: dialogue, sfx, music, ambience. "
        + _evidence(endpoint)
        + "Spans and hint times are seconds; boxes are [x0,y0,x1,y1] normalized "
        "to 0..1. Offscreen sources have visual_hint=null. Return JSON with a "
        "sources list. Each source follows this schema: "
        + json.dumps(SourcePlan.model_json_schema()),
        f"Video duration: {duration:g} seconds. Feedback: "
        + json.dumps([issue.model_dump() for issue in feedback]),
        parts,
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
    """Ask the validator model, per source, whether it appears in its own spans."""
    endpoint = Settings().validator_endpoint()
    hears = _hears(endpoint)
    if hears:
        sense = "Decide whether the source is seen or heard there. "
    else:
        # The model cannot hear: judge by whether the named producer is shown.
        # "Plausibly audible" alone accepted absent producers (a dog) in tests.
        sense = (
            "You cannot hear audio, so judge by the sound's producer. First name "
            "what is visible in the clips. Answer true only if the specific "
            "producer named in the source (the same kind of person, creature or "
            "object, or the action causing it) is visible; a sound with no visual "
            "trace, like a grunt or a voice, is true if that producer is shown. "
            "Answer false if the producer is a different or absent thing, e.g. a "
            "dog when only humans or monsters are shown. Put what you saw in the "
            "reason. "
        )
    shown = "video clips" if endpoint.input == "video" else "video frames"
    system = (
        f"You verify one planned sound source against {shown} from its time "
        "ranges. "
        + sense
        + 'Return JSON {"present": true or false, "reason": "one short sentence"}.'
    )
    duration, _ = media.probe(video)
    issues = []
    for source in plans:
        if not hears and source.kind in ("music", "ambience"):
            # Usually nothing visible makes these; without audio there is no evidence.
            continue
        windows = [(s.start, s.end) for s in source.spans] or [(0.0, duration)]
        with TemporaryDirectory() as tmp:
            parts = _media(video, endpoint, windows, Path(tmp))
        text = (
            "Source: "
            + json.dumps(source.model_dump(include={"name", "kind", "description"}))
            + ". Time ranges in seconds: "
            + ", ".join(f"{start:g}-{end:g}" for start, end in windows)
        )
        try:
            check = _request(endpoint, system, text, parts, _Check)
        except _InvalidJSON:
            logging.getLogger(__name__).warning(
                "plan validator returned invalid JSON twice for %s; treating as present",
                source.name,
            )
            continue
        if not check.present:
            issues.append(
                PlanIssue(
                    source_name=source.name,
                    kind="not_found",
                    message=f"{source.name}: "
                    + (check.reason or "not found in its time ranges"),
                )
            )
    return issues
