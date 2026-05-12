"""
Speech-to-Text (STT) module.

Supports two engines:
  - whisper-api  : OpenAI Whisper API — fast, accurate, needs API key
  - whisper-local: openai-whisper local model — offline, slower, no key needed

Flow:
  1. Record audio from the microphone into a WAV buffer
  2. Pass the buffer to the chosen STT engine
  3. Return the transcribed text string
"""

from __future__ import annotations

import io
import tempfile
import wave
from pathlib import Path

import pyaudio

from assistant.config import STTEngine, get_settings
from assistant.logger import get_logger

log = get_logger(__name__)

# ── Audio recording constants ──────────────────────────────────────────────────
_CHUNK = 1024          # frames per buffer read
_FORMAT = pyaudio.paInt16
_CHANNELS = 1          # mono
_RATE = 16_000         # 16 kHz — optimal for Whisper
_SILENCE_THRESHOLD = 500   # RMS below this = silence
_SILENCE_DURATION = 2.0    # seconds of silence to auto-stop recording
_MAX_DURATION = 60.0   # hard cap: 60 seconds per recording


class SpeechToText:
    """
    Records audio from the microphone and transcribes it.

    Usage:
        stt = SpeechToText()
        text = stt.transcribe()   # blocks until speech is detected and silence follows
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._engine = self._settings.stt_engine
        log.info(f"STT engine: [bold]{self._engine}[/bold]")

    # ── Public API ────────────────────────────────────────────────────────────

    def transcribe(self, on_recording_start: callable = None) -> str:  # type: ignore[type-arg]
        """
        Record from the microphone and return the transcribed text.

        Args:
            on_recording_start: Optional callback fired when recording begins
                                (useful to update UI — e.g. show a mic indicator).

        Returns:
            Transcribed text as a string, or "" if nothing was heard.
        """
        audio_bytes = self._record(on_start=on_recording_start)
        if not audio_bytes:
            log.warning("No audio recorded.")
            return ""
        return self._transcribe_bytes(audio_bytes)

    def transcribe_file(self, path: str | Path) -> str:
        """Transcribe an existing audio file (WAV, MP3, M4A, etc.)."""
        with open(path, "rb") as f:
            audio_bytes = f.read()
        return self._transcribe_bytes(audio_bytes, filename=str(path))

    # ── Recording ─────────────────────────────────────────────────────────────

    def _record(self, on_start: callable = None) -> bytes | None:  # type: ignore[type-arg]
        """Record from the default microphone until silence is detected."""
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=_FORMAT,
            channels=_CHANNELS,
            rate=_RATE,
            input=True,
            frames_per_buffer=_CHUNK,
        )

        log.info("🎤 Listening... (speak now)")
        if on_start:
            on_start()

        frames: list[bytes] = []
        silent_chunks = 0
        silence_limit = int(_SILENCE_DURATION * _RATE / _CHUNK)
        max_chunks = int(_MAX_DURATION * _RATE / _CHUNK)
        started = False

        try:
            for _ in range(max_chunks):
                data = stream.read(_CHUNK, exception_on_overflow=False)
                rms = self._rms(data)

                if rms > _SILENCE_THRESHOLD:
                    started = True
                    silent_chunks = 0
                    frames.append(data)
                elif started:
                    frames.append(data)
                    silent_chunks += 1
                    if silent_chunks >= silence_limit:
                        log.info("🔇 Silence detected — stopping recording.")
                        break
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        if not frames:
            return None

        return self._frames_to_wav_bytes(frames)

    # ── Transcription ─────────────────────────────────────────────────────────

    def _transcribe_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        if self._engine == STTEngine.WHISPER_API:
            return self._whisper_api(audio_bytes, filename)
        elif self._engine == STTEngine.WHISPER_LOCAL:
            return self._whisper_local(audio_bytes)
        else:
            raise ValueError(f"Unknown STT engine: {self._engine}")

    def _whisper_api(self, audio_bytes: bytes, filename: str) -> str:
        """Send audio to OpenAI Whisper API."""
        from openai import OpenAI  # noqa: PLC0415

        client = OpenAI(api_key=self._settings.openai_api_key.get_secret_value())
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename if filename.endswith(".wav") else "audio.wav"

        log.debug("Sending audio to Whisper API...")
        transcript = client.audio.transcriptions.create(
            model=self._settings.whisper_model,
            file=audio_file,
            response_format="text",
        )
        text = str(transcript).strip()
        log.info(f"Transcribed: [italic]{text!r}[/italic]")
        return text

    def _whisper_local(self, audio_bytes: bytes) -> str:
        """Transcribe using the local whisper model (no internet required)."""
        try:
            import whisper  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "Local Whisper not installed. Run: pip install openai-whisper"
            ) from exc

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
    def _rms(data: bytes) -> float:
        """Root-mean-square energy of a PCM audio chunk."""
        import array
        import math
        shorts = array.array("h", data)
        if not shorts:
            return 0.0
        mean_sq = sum(s * s for s in shorts) / len(shorts)
        return math.sqrt(mean_sq)

    @staticmethod
    def _frames_to_wav_bytes(frames: list[bytes]) -> bytes:
        """Pack raw PCM frames into an in-memory WAV file."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(_FORMAT))
            wf.setframerate(_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()
