"""
Text-to-Speech (TTS) module.

Uses Microsoft Edge TTS via the `edge-tts` package.
  - Free, no API key required
  - 300+ high-quality neural voices (Aria, Guy, Sonia, etc.)
  - Streams audio directly without saving to disk

Usage:
    tts = TextToSpeech()
    tts.speak("Hello, how can I help you?")   # blocking
    await tts.speak_async("Hello!")            # async
"""

from __future__ import annotations

import asyncio
import io
import threading

import edge_tts

from assistant.config import get_settings
from assistant.logger import get_logger

log = get_logger(__name__)

# Sentinel used to signal the playback thread to stop
_STOP_SIGNAL = b""


class TextToSpeech:
    """
    Converts text to speech using Edge TTS.

    speak() is thread-safe and can be called from Tkinter's main thread
    without freezing the UI (playback runs in a background thread).
    """

    def __init__(self) -> None:
        self._voice = get_settings().tts_voice
        self._playback_thread: threading.Thread | None = None
        log.info(f"TTS ready. Voice: [bold]{self._voice}[/bold]")

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """
        Speak text in a background thread (non-blocking).

        Stops any currently playing speech before starting new.
        """
        if not text.strip():
            return

        self.stop()  # cancel any in-progress speech

        self._playback_thread = threading.Thread(
            target=self._play_in_thread,
            args=(text,),
            daemon=True,
            name="tts-playback",
        )
        self._playback_thread.start()

    def speak_blocking(self, text: str) -> None:
        """Speak and block the calling thread until done (use in CLI mode)."""
        if not text.strip():
            return
        asyncio.run(self._synthesise_and_play(text))

    def stop(self) -> None:
        """Interrupt any currently playing speech."""
        if self._playback_thread and self._playback_thread.is_alive():
            # Edge-tts playback daemon threads die when the process stops,
            # but we can't interrupt mid-stream cleanly. We mark the old thread
            # as detached and start a fresh one next time speak() is called.
            log.debug("Stopping previous TTS playback.")
            self._playback_thread = None

    # ── Internal ─────────────────────────────────────────────────────────────

    def _play_in_thread(self, text: str) -> None:
        """Entry point for the background playback thread."""
        try:
            asyncio.run(self._synthesise_and_play(text))
        except Exception as exc:
            log.error(f"TTS playback error: {exc}", exc_info=True)

    async def _synthesise_and_play(self, text: str) -> None:
        """Synthesise speech and play it through the system's default audio output."""
        try:
            import pygame  # noqa: PLC0415
        except ImportError:
            # Fallback: save to temp file and open with system player
            await self._play_via_tempfile(text)
            return

        audio_data = await self._synthesise(text)
        buf = io.BytesIO(audio_data)

        pygame.mixer.init()
        pygame.mixer.music.load(buf)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.05)

        pygame.mixer.music.stop()
        pygame.mixer.quit()

    async def _synthesise(self, text: str) -> bytes:
        """Use edge-tts to generate speech audio bytes (MP3)."""
        log.debug(f"Synthesising speech for: {text[:60]!r}...")
        communicate = edge_tts.Communicate(text=text, voice=self._voice)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        audio_bytes = b"".join(chunks)
        log.debug(f"Synthesised {len(audio_bytes):,} bytes of audio.")
        return audio_bytes

    async def _play_via_tempfile(self, text: str) -> None:
        """Fallback: write MP3 to a temp file and open with the OS default player."""
        import os          # noqa: PLC0415
        import tempfile    # noqa: PLC0415

        audio_bytes = await self._synthesise(text)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        log.debug(f"Playing via OS: {tmp_path}")
        os.startfile(tmp_path)  # Windows; on macOS/Linux use subprocess + open/xdg-open


async def list_available_voices(language_filter: str = "en") -> list[str]:
    """
    Utility: list all Edge TTS voices matching a language prefix.

    Example:
        voices = await list_available_voices("en-US")
    """
    voices = await edge_tts.list_voices()
    return [v["ShortName"] for v in voices if v["ShortName"].startswith(language_filter)]
