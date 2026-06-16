"""
Offline and online speech-to-text for the voice assistant.

Engines (STT_ENGINE in .env):
  - faster-whisper: local, low-latency (recommended offline)
  - whisper: local OpenAI Whisper
  - google: online Google Speech API via SpeechRecognition
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any

import speech_recognition as sr
from dotenv import load_dotenv

load_dotenv()

VALID_ENGINES = frozenset({"google", "whisper", "faster-whisper"})
DEFAULT_ENGINE = "faster-whisper"

_model_lock = threading.Lock()
_faster_whisper_models: dict[tuple[str, str, str], Any] = {}
_openai_whisper_models: dict[tuple[str, str | None], Any] = {}


@dataclass(frozen=True)
class STTConfig:
    engine: str
    model: str
    language: str
    device: str
    compute_type: str
    preload: bool

    @property
    def is_offline(self) -> bool:
        return self.engine in ("whisper", "faster-whisper")


def load_stt_config() -> STTConfig:
    engine = os.getenv("STT_ENGINE", DEFAULT_ENGINE).strip().lower()
    if engine not in VALID_ENGINES:
        print(f"Unknown STT_ENGINE '{engine}', using '{DEFAULT_ENGINE}'.")
        engine = DEFAULT_ENGINE

    return STTConfig(
        engine=engine,
        model=os.getenv("WHISPER_MODEL", "base").strip() or "base",
        language=os.getenv("WHISPER_LANGUAGE", "en").strip() or "en",
        device=os.getenv("WHISPER_DEVICE", "cpu").strip() or "cpu",
        compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip() or "int8",
        preload=os.getenv("STT_PRELOAD", "true").strip().lower() in ("1", "true", "yes"),
    )


def _faster_whisper_init_options(config: STTConfig) -> dict[str, str]:
    opts: dict[str, str] = {"compute_type": config.compute_type}
    if config.device and config.device != "auto":
        opts["device"] = config.device
    return opts


def _get_faster_whisper_model(config: STTConfig):
    key = (config.model, config.device, config.compute_type)
    with _model_lock:
        if key not in _faster_whisper_models:
            from faster_whisper import WhisperModel

            print(
                f"Loading Faster-Whisper model '{config.model}' "
                f"(device={config.device}, compute_type={config.compute_type})..."
            )
            _faster_whisper_models[key] = WhisperModel(
                config.model, **_faster_whisper_init_options(config)
            )
            print("Faster-Whisper model ready.")
        return _faster_whisper_models[key]


def _get_openai_whisper_model(config: STTConfig):
    import whisper

    device = None if config.device in ("", "auto") else config.device
    key = (config.model, device)
    with _model_lock:
        if key not in _openai_whisper_models:
            print(f"Loading OpenAI Whisper model '{config.model}'...")
            load_kwargs: dict[str, Any] = {}
            if device:
                load_kwargs["device"] = device
            _openai_whisper_models[key] = whisper.load_model(config.model, **load_kwargs)
            print("OpenAI Whisper model ready.")
        return _openai_whisper_models[key]


def _audio_to_float32(audio_data: sr.AudioData):
    import numpy as np

    raw = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    return samples / 32768.0


def _recognize_faster_whisper(recognizer: sr.Recognizer, audio_data: sr.AudioData, config: STTConfig) -> str:
    model = _get_faster_whisper_model(config)
    audio = _audio_to_float32(audio_data)
    segments, _info = model.transcribe(
        audio,
        language=config.language,
        beam_size=1,
        vad_filter=True,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def _recognize_openai_whisper(recognizer: sr.Recognizer, audio_data: sr.AudioData, config: STTConfig) -> str:
    model = _get_openai_whisper_model(config)
    audio = _audio_to_float32(audio_data)
    result = model.transcribe(audio, language=config.language)
    return (result.get("text") or "").strip()


def _recognize_google(recognizer: sr.Recognizer, audio_data: sr.AudioData, config: STTConfig) -> str:
    return recognizer.recognize_google(audio_data, language=f"{config.language}-US")


def preload_whisper_model(config: STTConfig | None = None) -> None:
    """Load the local Whisper model in a background thread at startup."""
    cfg = config or load_stt_config()
    try:
        if cfg.engine == "faster-whisper":
            _get_faster_whisper_model(cfg)
        elif cfg.engine == "whisper":
            _get_openai_whisper_model(cfg)
    except Exception as exc:
        print(f"STT preload failed ({cfg.engine}): {exc}")


def recognize_text(
    recognizer: sr.Recognizer,
    audio_data: sr.AudioData,
    config: STTConfig | None = None,
) -> str:
    """
    Transcribe audio using the configured engine.
    Raises sr.UnknownValueError if no speech was detected.
    Raises sr.RequestError for network/API failures (google engine).
    """
    cfg = config or load_stt_config()

    if cfg.engine == "faster-whisper":
        text = _recognize_faster_whisper(recognizer, audio_data, cfg)
    elif cfg.engine == "whisper":
        text = _recognize_openai_whisper(recognizer, audio_data, cfg)
    else:
        text = _recognize_google(recognizer, audio_data, cfg)

    if not text:
        raise sr.UnknownValueError("No speech detected")
    return text


def stt_status_message(config: STTConfig | None = None) -> str:
    cfg = config or load_stt_config()
    if cfg.is_offline:
        return f"offline ({cfg.engine}, model={cfg.model})"
    return "online (google)"
