"""
Speech-to-Text (STT) module.

Uses sounddevice for microphone recording — works on Windows, macOS, and Linux
with no C++ compiler needed.

Supports two transcription engines:
  - whisper-api  : OpenAI Whisper API — fast, accurate, needs API key
  - whisper-local: openai-whisper local model — offline, no key needed

Flow:
  1. Record audio from the microphone using sounddevice
  2. Auto-stop after a period of silence
  3. Send the audio bytes to the chosen STT engine
  4. Return the transcribed text string
"""

from __future__ import annotations

import io
import queue
import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from assistant.config import STTEngine, get_settings
from assistant.logger import get_logger

log = get_logger(__name__)

# ── Audio recording constants ──────────────────────────────────────────────────
_SAMPLE_RATE = 16_000  # 16 kHz — optimal for Whisper
_CHANNELS = 1  # mono
_DTYPE = "int16"  # 16-bit PCM
_BLOCK_SIZE = 1024  # frames per callback block
_SILENCE_THRESHOLD = 600  # RMS below this = silence (raised to reduce noise pickup)
_SILENCE_DURATION = 2.0  # seconds of silence before auto-stop
_MAX_DURATION = 60.0  # hard cap: 60 seconds per recording


class SpeechToText:
    """
    Records audio from the microphone and transcribes it to text.

    Usage:
        stt = SpeechToText()
        text = stt.transcribe()   # blocks until speech + silence detected
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._engine = self._settings.stt_engine
        log.info(f"STT engine: [bold]{self._engine}[/bold]")

    # ── Public API ────────────────────────────────────────────────────────────

    def transcribe(self, on_recording_start: callable | None = None) -> str:  # type: ignore[type-arg]
        """
        Record from the microphone and return the transcribed text.

        Args:
            on_recording_start: Optional callback fired when recording begins.
                                Use this to update the UI (e.g. show mic indicator).

        Returns:
            Transcribed text as a string, or "" if nothing was heard.
        """
        audio_bytes = self._record(on_start=on_recording_start)
        if not audio_bytes:
            log.warning("No audio recorded.")
            return ""
        return self._transcribe_bytes(audio_bytes)

    def transcribe_file(self, path: str | Path) -> str:
        """Transcribe an existing audio file (WAV, MP3, FLAC, etc.)."""
        with open(path, "rb") as f:
            audio_bytes = f.read()
        return self._transcribe_bytes(audio_bytes, filename=str(path))

    # ── Recording ─────────────────────────────────────────────────────────────

    def _record(self, on_start: callable | None = None) -> bytes | None:  # type: ignore[type-arg]
        """
        Record from the default microphone until silence is detected.
        Uses sounddevice — works on Python 3.14+ without any compiler.
        """
        audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        stop_event = threading.Event()
        frames: list[np.ndarray] = []
        silent_blocks = 0
        started = False  # True once we've heard non-silent audio

        silence_limit = int(_SILENCE_DURATION * _SAMPLE_RATE / _BLOCK_SIZE)
        max_blocks = int(_MAX_DURATION * _SAMPLE_RATE / _BLOCK_SIZE)
        block_count = 0

        def callback(
            indata: np.ndarray,
            frame_count: int,
            time_info: object,
            status: sd.CallbackFlags,
        ) -> None:
            nonlocal started, silent_blocks, block_count
            if status:
                log.debug(f"sounddevice status: {status}")

            audio_queue.put(indata.copy())
            block_count += 1

            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))

            if rms > _SILENCE_THRESHOLD:
                started = True
                silent_blocks = 0
            elif started:
                silent_blocks += 1
                if silent_blocks >= silence_limit:
                    stop_event.set()

            if block_count >= max_blocks:
                stop_event.set()

        log.info("🎤 Listening... (speak now)")
        if on_start:
            on_start()

        with sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=_CHANNELS,
            dtype=_DTYPE,
            blocksize=_BLOCK_SIZE,
            callback=callback,
        ):
            stop_event.wait()

        # Drain the queue into frames
        while not audio_queue.empty():
            frames.append(audio_queue.get_nowait())

        if not frames or not started:
            return None

        log.info("🔇 Silence detected — stopped recording.")
        audio_data = np.concatenate(frames, axis=0)
        return self._array_to_wav_bytes(audio_data)

    # ── Transcription ─────────────────────────────────────────────────────────

    def _transcribe_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        if self._engine == STTEngine.WHISPER_API:
            return self._whisper_api(audio_bytes, filename)
        elif self._engine == STTEngine.WHISPER_LOCAL:
            return self._whisper_local(audio_bytes)
        else:
            raise ValueError(f"Unknown STT engine: {self._engine}")

    def _whisper_api(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Send audio bytes to the OpenAI Whisper API."""
        from openai import OpenAI

        client = OpenAI(api_key=self._settings.openai_api_key.get_secret_value())
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"

        log.debug("Sending audio to Whisper API...")
        transcript = client.audio.transcriptions.create(
            model=self._settings.whisper_model,
            file=audio_file,
            response_format="text",
            language="en",  # force English — prevents garbled noise being read as other languages
        )
        text = str(transcript).strip()
        log.info(f"Transcribed: [italic]{text!r}[/italic]")
        return text

    def _whisper_local(self, audio_bytes: bytes) -> str:
        """Transcribe using the local whisper model (no internet required)."""
        try:
            import whisper
        except ImportError as exc:
            raise ImportError(
                "Local Whisper not installed. Run: pip install openai-whisper"
            ) from exc

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        model = whisper.load_model("base")
        result = model.transcribe(tmp_path)
        text = str(result.get("text", "")).strip()
        Path(tmp_path).unlink(missing_ok=True)
        log.info(f"Transcribed (local): [italic]{text!r}[/italic]")
        return text

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _array_to_wav_bytes(audio: np.ndarray) -> bytes:
        """Convert a NumPy int16 array to WAV bytes in memory."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(2)  # 2 bytes = int16
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()
