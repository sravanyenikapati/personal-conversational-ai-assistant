"""
Text-to-Speech (TTS) module.

Uses Microsoft Edge TTS for synthesis (free, no API key, 300+ neural voices).
Decodes MP3 output via soundfile (bundled libsndfile 1.2+ has MP3 support).
Plays audio directly through speakers via sounddevice.

No media player popup. No extra packages. Works on Python 3.14+.

Usage:
    tts = TextToSpeech()
    tts.speak("Hello, how can I help you?")   # non-blocking
"""

from __future__ import annotations

import asyncio
import io
import threading

import sounddevice as sd
import soundfile as sf

from assistant.config import get_settings
from assistant.logger import get_logger

log = get_logger(__name__)


class TextToSpeech:
    """
    Converts text to speech and plays it through the system speakers.

    speak() is non-blocking — plays in a background thread so the UI
    stays responsive while the assistant is talking.
    """

    def __init__(self) -> None:
        self._voice = get_settings().tts_voice
        self._playback_thread: threading.Thread | None = None
        self._stop_flag = threading.Event()
        log.info(f"TTS ready. Voice: [bold]{self._voice}[/bold]")

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Speak text through the speakers (non-blocking)."""
        if not text.strip():
            return

        self.stop()
        self._stop_flag.clear()

        self._playback_thread = threading.Thread(
            target=self._run,
            args=(text,),
            daemon=True,
            name="tts-playback",
        )
        self._playback_thread.start()

    def stop(self) -> None:
        """Stop any currently playing speech immediately."""
        self._stop_flag.set()
        sd.stop()
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=2.0)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self, text: str) -> None:
        """Thread entry point."""
        try:
            asyncio.run(self._synthesise_and_play(text))
        except Exception as exc:
            log.error(f"TTS error: {exc}", exc_info=True)

    async def _synthesise_and_play(self, text: str) -> None:
        """Synthesise MP3 via Edge TTS → decode with soundfile → play via sounddevice."""
        mp3_bytes = await self._synthesise_mp3(text)

        if not mp3_bytes or self._stop_flag.is_set():
            return

        # Decode MP3 → float32 PCM array
        # soundfile 0.12+ bundles libsndfile 1.1+ which natively decodes MP3
        buf = io.BytesIO(mp3_bytes)
        try:
            audio_data, sample_rate = sf.read(buf, dtype="float32")
        except Exception as exc:
            log.error(f"Failed to decode TTS audio: {exc}", exc_info=True)
            return

        if self._stop_flag.is_set():
            return

        log.debug(
            f"Playing {len(audio_data) / sample_rate:.1f}s of audio "
            f"@ {sample_rate} Hz..."
        )

        # Play through default speakers
        sd.play(audio_data, samplerate=sample_rate)

        # Wait for playback, honouring stop requests every 50ms
        while sd.get_stream().active:
            if self._stop_flag.is_set():
                sd.stop()
                return
            await asyncio.sleep(0.05)

        sd.wait()
        log.debug("Playback complete.")

    async def _synthesise_mp3(self, text: str) -> bytes:
        """Fetch MP3 audio bytes from Microsoft Edge TTS."""
        import edge_tts  # noqa: PLC0415

        # Strip non-ASCII characters — English TTS voice cannot speak other scripts
        clean_text = text.encode("ascii", errors="ignore").decode("ascii").strip()
        if not clean_text:
            log.warning("TTS skipped — text contained no speakable ASCII characters.")
            return b""

        log.debug(f"Synthesising: {clean_text[:60]!r}...")
        communicate = edge_tts.Communicate(text=clean_text, voice=self._voice)

        chunks: list[bytes] = []
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
        except edge_tts.exceptions.NoAudioReceived:
            log.warning("TTS: No audio received from Edge TTS — skipping playback.")
            return b""

        mp3_bytes = b"".join(chunks)
        log.debug(f"Received {len(mp3_bytes):,} bytes from Edge TTS.")
        return mp3_bytes


async def list_available_voices(language_filter: str = "en") -> list[str]:
    """
    Utility: list all Edge TTS voices matching a language prefix.

    Example:
        import asyncio
        voices = asyncio.run(list_available_voices("en-US"))
    """
    import edge_tts  # noqa: PLC0415
    voices = await edge_tts.list_voices()
    return [v["ShortName"] for v in voices if v["ShortName"].startswith(language_filter)]
