from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUDYSSEY_")

    planner: Literal["stub", "real"] = "stub"
    separator: Literal["stub", "real", "remote"] = "stub"
    filter: Literal["stub", "real", "remote"] = "stub"
    grounder: Literal["stub", "real", "remote"] = "stub"
    grounding_url: str = ""
    generator: Literal["stub", "real", "remote"] = "stub"
    generator_url: str = ""
    gen_base_model: str = "jnwnlee/SelVA"
    gen_model: str = "sogang-audyssey/internal-model"
    gen_generator_file: str = "generator/S_O_s43/model_ema_step1000.pth"
    gen_encoder_file: str = "encoder/S_O/best.pt"
    gen_device: str = "cuda"
    gen_steps: int = 25
    gen_cfg: float = 4.5
    gen_seed: int = 42
    gen_single_max_s: float = 15
    gen_window_s: float = 8
    max_generation_retries: int = Field(default=2, ge=0)
    generation_margin_threshold: float = 0.0
    # Visual prompting (SAM3 locate + masked video for SAM Audio) is off by default:
    # with a text description the mask barely changed separation in our tests.
    visual_prompt: bool = False
    sam3_model: str = "facebook/sam3.1"
    sam3_device: str = "cuda"
    # SAM3 keeps per-frame tracking state on the GPU; 1080p60 at 4 fps already needs >24 GB.
    # 0 tracks at the source frame rate.
    sam3_track_fps: float = Field(default=2, ge=0)
    separator_url: str = ""
    filter_url: str = ""
    tool_token: str = Field(default="", repr=False)
    remote_timeout_s: float = Field(default=600, gt=0)
    planner_base_url: str = ""
    planner_frames: int = Field(default=4, ge=1, le=16)
    planner_model: str = ""
    planner_api_key: str = Field(default="", repr=False)
    # openai: Chat Completions (OpenAI, vLLM, Gemini's OpenAI endpoint).
    # gemini: native generateContent, the only Gemini path that accepts video.
    planner_api: Literal["openai", "gemini"] = "openai"
    # frames: planner_frames JPEGs. video: one downscaled clip sampled at planner_fps
    # (vLLM video_url or Gemini inline video; OpenAI's API takes frames only).
    planner_input: Literal["frames", "video"] = "frames"
    planner_fps: float = Field(default=1, gt=0, le=30)
    # Video input only: keep the clip's audio (Gemini, or vLLM Omni use_audio_in_video).
    planner_video_audio: bool = False
    max_plan_rounds: int = Field(default=2, ge=1)
    max_separation_retries: int = Field(default=2, ge=0)
    max_duration_s: float = Field(default=30, gt=0)
    # Per uploaded file, on the app and the tool server; checked while streaming.
    max_upload_mb: float = Field(default=200, gt=0)
    work_dir: Path = Path("work/jobs")
    sam_audio_model: str = "facebook/sam-audio-large-tv"
    sam_audio_judge_model: str = "facebook/sam-audio-judge"
    sam_audio_device: str = "cuda"
    sam_audio_reranking_candidates: int = Field(default=1, ge=1)
    sam_audio_predict_spans: bool = False
    # Reranking (candidates > 1) only: CLAP and ImageBind checkpoint files. Empty CLAP
    # uses the cached lukewys/laion_clap 630k-best.pt; empty ImageBind disables the
    # visual ranker, so masked videos fall back to the text rankers (CLAP + Judge).
    sam_audio_clap_checkpoint: str = ""
    sam_audio_imagebind_checkpoint: str = ""
    judge_pass_threshold: float = 0.5

    @model_validator(mode="after")
    def _gemini_takes_video(self) -> Self:
        if self.planner_api == "gemini" and self.planner_input != "video":
            raise ValueError(
                "AUDYSSEY_PLANNER_API=gemini requires AUDYSSEY_PLANNER_INPUT=video"
            )
        return self
