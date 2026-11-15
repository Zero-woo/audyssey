# 플래너 모델 조사: 지원 모델, 입력 구조, 비용

2026-11-15 기준 공식 문서 조사입니다. 가격과 모델 목록은 자주 바뀌므로 쓰기 전에 [출처](#출처)의 원문을 다시 확인합니다.
플래너와 검증기는 같은 설정(`AUDYSSEY_PLANNER_*`)을 쓰므로 아래 선택은 둘에 함께 적용됩니다.

## 요약

| 경로 | 영상 직접 입력 | 시간 정보 전달 | 오디오 함께 | 이 코드의 설정 |
|---|---|---|---|---|
| Gemini 네이티브 API (`generateContent`) | 됨. `video_metadata.fps`로 샘플링 조절 | 모델이 영상 시간축을 직접 받음 | 됨 (영상의 오디오 트랙) | `AUDYSSEY_PLANNER_API=gemini` |
| Gemini OpenAI 호환 엔드포인트 | 안 됨 (이미지·오디오만) | 프레임마다 시각 텍스트 | 별도 `input_audio`만 | `AUDYSSEY_PLANNER_API=openai`, `INPUT=frames` |
| OpenAI API | 안 됨. 공식 권장은 프레임 샘플링 | 프레임마다 시각 텍스트 | 비전 모델은 오디오 입력 없음 | `AUDYSSEY_PLANNER_API=openai`, `INPUT=frames` |
| vLLM (Qwen-VL, Qwen-Omni) | 됨. `video_url` + 요청별 fps | Qwen2.5-VL은 절대 시간 mRoPE, Qwen3-VL은 프레임 시각 텍스트 | Omni만 (`use_audio_in_video`) | `AUDYSSEY_PLANNER_API=openai`, `INPUT=video` |

## 현재 입력 방식 (frames)

- `AUDYSSEY_PLANNER_FRAMES`장(기본 4)을 영상 전체에서 고르게 뽑습니다. fps가 아니라 **총 장수**입니다. 7초 영상이면 약 1.8초 간격입니다.
- 각 구간의 중간 시점에서 한 장씩, 가로 최대 512px JPEG로 뽑습니다(`media.extract_frames`).
- 순서는 메시지 안의 위치와 텍스트로 알려 줍니다. 이미지마다 바로 앞에 `Frame at 1.78 seconds` 텍스트 파트를 붙여 시간순으로 보냅니다.
- 오디오는 보내지 않습니다.

## Gemini

**입력 구조 (네이티브 `generateContent`, 실제 호출로 확인)**

```json
{
  "system_instruction": {"parts": [{"text": "..."}]},
  "contents": [{"role": "user", "parts": [
    {"inline_data": {"mime_type": "video/mp4", "data": "<base64>"}, "video_metadata": {"fps": 1}},
    {"text": "..."}
  ]}],
  "generationConfig": {"responseMimeType": "application/json"}
}
```

- inline 전송은 요청 전체 20MB 미만일 때만 씁니다. 그보다 크면 Files API(파일당 2GB, 48시간 보관)를 써야 합니다. 이 코드는 영상을 가로 512px로 다시 인코딩해 inline으로 보냅니다(7초 샘플 148KB).
- 기본 샘플링은 1fps입니다. 문서에 상한은 없습니다.
- 프레임당 토큰은 Gemini 4·3 계열 70(HIGH 해상도 280), Gemini 2.5 계열 64(LOW)~256입니다. 오디오는 초당 25토큰(2.5 계열 32)입니다.
- 실측(`gemini-3.5-flash-lite`, 7.1초 샘플): 1fps에서 영상 토큰 637, 4fps에서 2,023.
- 영상의 오디오 트랙도 모델에 들어갑니다(1Kbps 단일 채널).
- 플래너 실측(`gemini-3.5-flash-lite`, fps 2, 샘플): 오디오를 넣으면 `sword slash sound`, `grunt sound`를 찾았고, 오디오를 빼면 `game ambience` 하나만 찾았습니다. 플래너 약 3초, 검증기 약 2초.
- OpenAI 호환 엔드포인트는 이미지와 `input_audio`만 받고 영상은 받지 않습니다. 영상은 네이티브 API로만 보낼 수 있습니다.
- 문서 기본값은 새 Interactions API(`/v1beta/interactions`)로 바뀌었지만, `generateContent`도 "legacy, 계속 완전 지원"으로 남아 있습니다.

**모델과 가격** (Standard, 100만 토큰당 USD; 입력은 텍스트·이미지·영상)

| 모델 | 상태 | 무료 등급 | 입력 | 오디오 입력 | 출력 |
|---|---|---|---|---|---|
| `gemini-4-hydrogen` | 2026-11-12 출시 | 있음 | 1.50 | 별도 표기 없음 | 7.50 |
| `gemini-4-carbon` | 2026-11-10 출시 | 없음 | 2.00 (11-30까지), 이후 4.00 | 별도 표기 없음 | 10.00, 이후 20.00 |
| `gemini-4-argon` | 2026-10-13 출시 | 없음 | 2.00 (11-30까지), 이후 4.00 | 별도 표기 없음 | 10.00, 이후 20.00 |
| `gemini-3.8-flash` | GA | 있음 | 0.75 (12-31까지), 이후 1.50 | 별도 표기 없음 | 3.75, 이후 7.50 |
| `gemini-3.6-flash` | GA (이전 세대) | 있음 | 0.75 (12-31까지), 이후 1.50 | 별도 표기 없음 | 3.75, 이후 7.50 |
| `gemini-3.5-flash-lite` | GA | 있음 | 0.30 | 0.30 | 2.50 |
| `gemini-3.1-flash-lite` | GA, 2027-05-07 종료 | 있음 | 0.25 | 0.50 | 1.50 |
| `gemini-3.1-pro-preview` | preview | 없음 | 2.00 (200k 초과 4.00) | 별도 표기 없음 | 12.00 (200k 초과 18.00) |
| `gemini-3-flash-preview` | preview | 있음 | 0.50 | 1.00 | 3.00 |
| `gemini-2.5-flash-lite` | 기존 사용자만 | 있음 | 0.10 | 0.30 | 0.40 |

- 위 모델은 모두 영상 입력을 지원합니다.
- `gemini-2.5-flash`와 `gemini-2.5-pro`는 2026-12-01 종료됩니다(각각 3.5-flash-lite, 3.8-flash로 자동 라우팅).
- `gemini-3.7-flash`는 3.8-flash로, `gemini-3.5-flash`는 3.6-flash로 자동 라우팅됩니다.

## OpenAI

**영상 입력: 지원 모델 없음.** 모델 페이지는 최신 모델 모두 "텍스트·이미지 입력, 텍스트 출력"이라고 하고, `gpt-6.1-sol`·`gpt-6.1-terra` 페이지는 영상과 오디오를 지원하지 않는다고 명시합니다. 공식 쿡북은 "영상을 API에 직접 보낼 수 없으니 프레임을 샘플링해 이미지로 보내라"고 안내합니다. 그래서 OpenAI는 frames 방식이 공식 방식입니다.

**입력 구조 (Chat Completions, 이 코드가 쓰는 방식)**

```json
{"role": "user", "content": [
  {"type": "text", "text": "Frame at 0.89 seconds"},
  {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,<B64>", "detail": "auto"}}
]}
```

- Responses API에서는 `{"type": "input_image", "image_url": "data:...", "detail": "low"}`입니다. OpenAI는 새 프로젝트에 Responses를 권장하지만 Chat Completions도 계속 지원합니다.
- 요청당 이미지 최대 1,500장, 요청 전체 512MB. PNG, JPEG, WEBP, 정지 GIF.
- `detail`: `auto`(기본), `low`, `high`, `original`. 패치 방식 모델은 32×32 패치 수 × 1.2가 토큰입니다. 예: 512×512 `low`는 256패치 → 약 308토큰.
- 오디오 입력은 `gpt-audio-1.5` 같은 별도 모델로 Chat Completions에서만 됩니다(이미지 입력 없음). 한 요청에 프레임과 오디오를 함께 넣을 수 없습니다.
- 구조화 출력은 `json_object`보다 `json_schema`(strict)를 권장합니다.

**모델과 가격** (Standard, 100만 토큰당 USD; 272k 초과 입력은 입력 2배, 출력 1.5배)

| 모델 | 컨텍스트 / 최대 출력 | 입력 | 캐시 입력 | 출력 |
|---|---|---|---|---|
| `gpt-6-astra` (기본 추천) | 1.05M / 128k | 10.00 | 1.00 | 50.00 |
| `gpt-6.1-sol` | 1.05M / 128k | 2.00 | 0.10 | 10.00 |
| `gpt-6.1-terra` | 1.05M / 128k | 1.00 | 0.05 | 5.00 |
| `gpt-6-luna` | 1.05M / 128k | 0.10 | 0.01 | 0.50 |
| `gpt-5.4-mini` | 확인 안 함 | 0.75 | 0.075 | 4.50 |
| `gpt-5.4-nano` | 확인 안 함 | 0.20 | 0.02 | 1.25 |
| `gpt-audio-1.5` (오디오) | 128k / 16k | 32.00 | – | 64.00 |

- Batch와 Flex는 Standard의 50%입니다.
- `gpt-6.1-sol`, `gpt-6.1-terra`, `gpt-6-luna`의 이미지 토큰 배수는 문서에 없습니다.

## vLLM (Qwen-VL, Qwen-Omni)

Compose의 `vllm/vllm-openai:v0.32.0` 기준입니다.

**입력 구조 (영상)**

```python
client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": [
        {"type": "video_url", "video_url": {"url": "data:video/mp4;base64,<B64>"}},
        {"type": "text", "text": "..."},
    ]}],
    response_format={"type": "json_object"},
    extra_body={
        "media_io_kwargs": {"video": {"fps": 1, "num_frames": -1}},
        "mm_processor_kwargs": {"use_audio_in_video": True},  # Omni만
    },
)
```

- URL은 `http(s)`, `data:video/mp4;base64,...`, `file://`(서버에 `--allowed-local-media-path` 필요)를 받습니다.
- 서버 기본은 영상 하나당 고르게 32프레임입니다. `fps`와 `num_frames`를 함께 주면 "둘 중 프레임이 더 적은 쪽"을 씁니다. `num_frames=-1`은 제한 없음이라 fps가 그대로 적용됩니다.
- 요청별 `media_io_kwargs`, `mm_processor_kwargs`는 서버를 `--trust-request-mm-kwargs`로 띄워야 받습니다.
- 시간 정보: Qwen2.5-VL은 프레임 fps로 mRoPE 시간 위치를 절대 시간에 맞춥니다. Qwen3-VL은 프레임 묶음마다 `<X.X seconds>` 텍스트를 넣습니다. 이미지를 따로 여러 장 보내면 이런 시간 정보가 없습니다.
- 영상 디코딩은 기본 opencv(CPU)이고 이미지에 포함돼 있습니다.
- 실측(Compose vLLM, `Qwen2.5-VL-3B-Instruct`, 512px로 줄인 7.1초 샘플): 프롬프트 토큰이 fps 0.5에서 382, 1에서 562, 2에서 1,282, 4에서 2,542로 늘어 요청별 fps가 적용됨을 확인했습니다.

**모델**

| 모델 | vLLM 지원 | 입력 | 크기 |
|---|---|---|---|
| Qwen2.5-VL | 됨 | 텍스트, 이미지 여러 장, 영상 여러 개 | 3B, 7B, 32B, 72B (AWQ 있음) |
| Qwen3-VL | 됨 | 텍스트, 이미지, 영상 | 2B, 4B, 8B, 32B, MoE 30B-A3B, 235B-A22B (Instruct, Thinking, FP8) |
| Qwen2.5-Omni | thinker만 (텍스트 출력) | 텍스트, 이미지, 영상, 오디오 | 3B, 7B |
| Qwen3-Omni | thinker만 (텍스트 출력) | 텍스트, 이미지, 영상, 오디오 | 30B-A3B Instruct, Thinking |

- Omni에서 영상의 오디오를 쓰려면 `mm_processor_kwargs.use_audio_in_video=true`입니다. 이때 mp4 전체가 오디오 크기 제한(`VLLM_MAX_AUDIO_CLIP_FILESIZE_MB`, 기본 25MB)을 받습니다. 이 코드는 512px로 줄여 보내므로 보통 제한 안쪽입니다.
- Qwen3-Omni README는 "vLLM serve에서 `use_audio_in_video`를 쓸 수 없다"고 하지만, vLLM v0.32 테스트는 이 경로를 검사합니다. 실제 서버에서 확인이 필요합니다.
- vLLM `v0.32.0` 이미지에 오디오 디코더(`av`, `soundfile`)가 들어 있는지는 확인하지 못했습니다.
- 메모리(transformers BF16, talker 포함, 30초 영상): Qwen2.5-Omni-3B 22.4GB, 7B 41.9GB, Qwen3-Omni-30B-A3B-Instruct 88.5GB. vLLM 수치는 없습니다.
- 비용은 GPU 사용 시간뿐입니다.

## 출처

**Gemini**
- [모델](https://aistudio.google.com/docs/models), [종료 일정](https://aistudio.google.com/docs/deprecations), [가격](https://aistudio.google.com/docs/pricing)
- [영상 이해 (generateContent)](https://aistudio.google.com/docs/video-understanding?generate-content=true), [미디어 해상도](https://aistudio.google.com/docs/media-resolution?generate-content=true)
- [구조화 출력](https://aistudio.google.com/docs/structured-output?generate-content=true), [Files API](https://aistudio.google.com/docs/files), [OpenAI 호환](https://aistudio.google.com/docs/openai), [Interactions API](https://aistudio.google.com/docs/interactions)

**OpenAI**
- [모델](https://developers.openai.com/api/docs/models), [가격](https://developers.openai.com/api/docs/pricing)
- [이미지와 비전](https://developers.openai.com/api/docs/guides/images-vision), [오디오](https://developers.openai.com/api/docs/guides/audio), [파일 입력](https://developers.openai.com/api/docs/guides/file-inputs)
- [구조화 출력](https://developers.openai.com/api/docs/guides/structured-outputs), [Responses 이전 안내](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [영상 이해 쿡북](https://developers.openai.com/cookbook/examples/gpt_with_vision_for_video_understanding)

**vLLM, Qwen**
- [vLLM 멀티모달 입력 v0.32.0](https://docs.vllm.ai/en/v0.32.0/features/multimodal_inputs/), [엔진 인자](https://docs.vllm.ai/en/v0.32.0/configuration/engine_args/), [지원 모델](https://docs.vllm.ai/en/v0.32.0/models/supported_models/), [구조화 출력](https://docs.vllm.ai/en/v0.32.0/features/structured_outputs/)
- [vLLM `use_audio_in_video` 테스트](https://github.com/vllm-project/vllm/blob/v0.32.0/tests/entrypoints/multimodal/openai/chat_completion/test_audio_in_video.py)
- [Qwen2.5-VL-3B](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct), [Qwen3-VL](https://github.com/QwenLM/Qwen3-VL), [Qwen2.5-Omni](https://github.com/QwenLM/Qwen2.5-Omni), [Qwen3-Omni](https://github.com/QwenLM/Qwen3-Omni)
