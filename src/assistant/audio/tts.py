"""
Text-to-Speech (TTS) module.

Uses Microsoft Edge TTS for synthesis (free, no API key, 300+ neural voices).
Decodes MP3 output via soundfile and plays directly through speakers via sounddevice.

Two modes:

  speak(text)               — Blocking full-text synthesis. Use for short replies
                              or when the complete text is already available.

  speak_stream(sentences)   — Pipelined streaming mode. Accepts an iterator of
                              complete sentences and plays each one as soon as it's
                              synthesised, while the next is being prepared in parallel.
                              This is the low-latency voice mode (like ChatGPT Voice).

The streaming mode dramatically reduces time-to-first-word:
  Before: user waits for full AI response + full TTS synthesis (~4-8s)
  After:  user hears first sentence within ~0.8-1.2s of finishing speaking

Usage:
    tts = TextToSpeech()

    # Standard (blocking, full reply):
    tts.speak("Hello, how can I help you today?")

    # Streaming (low-latency, sentence-by-sentence):
    for sentence in brain.stream_chat("Tell me about Mars."):
        # speak_stream handles this more efficiently — see below
        pass

    # Best usage for streaming:
    tts.speak_stream(brain.stream_chat("Tell me about Mars."))
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Iterator

import sounddevice as sd

from assistant.config import get_settings
from assistant.logger import get_logger

log = get_logger(__name__)


class TextToSpeech:
    """
    Converts text to speech and plays it through the system speakers.

    speak() is non-blocking for the caller — audio plays in a background thread.
    speak_stream() pipelines synthesis and playback for minimum latency.
    """

    def __init__(self) -> None:
        self._voice = get_settings().tts_voice
        self._playback_thread: threading.Thread | None = None
        self._stop_flag = threading.Event()
        log.info(f"TTS ready. Voice: [bold]{self._voice}[/bold]")

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """
        Speak text through the speakers (non-blocking for the caller).

        Synthesises the entire text first, then plays it. Use this when the
        full text is already available. For streaming AI responses, use
        speak_stream() instead to reduce time-to-first-word.

        Args:
            text: The text to speak. Empty / whitespace-only strings are ignored.
        """
        if not text.strip():
            return

        self.stop()
        self._stop_flag.clear()

        self._playback_thread = threading.Thread(
            target=self._run_single,
            args=(text,),
            daemon=True,
            name="tts-playback",
        )
        self._playback_thread.start()

    def speak_stream(self, sentence_iter: Iterator[str]) -> None:
        """
        Speak a stream of sentences with minimum latency (non-blocking for caller).

        Pipelines synthesis and playback:
          - A producer thread fetches each sentence from the iterator and synthesises it.
          - A consumer thread plays each synthesised chunk as soon as it's ready.
          - Both run concurrently so playback of sentence N overlaps with synthesis of N+1.

        This is the key to low-latency voice — the user hears the first sentence
        within ~0.8s of finishing speaking, instead of waiting 4-8s for the full
        response to be generated and synthesised.

        Args:
            sentence_iter: An iterator yielding complete sentences (from brain.stream_chat).

        Example:
            tts.speak_stream(brain.stream_chat("What's the best way to learn guitar?"))
            # Returns immediately; audio plays in background threads.
        """
        self.stop()
        self._stop_flag.clear()

        self._playback_thread = threading.Thread(
            target=self._run_stream,
            args=(sentence_iter,),
            daemon=True,
            name="tts-stream",
        )
        self._playback_thread.start()

    def stop(self) -> None:
        """Stop any currently playing speech immediately."""
        self._stop_flag.set()
        sd.stop()
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=2.0)

    def wait(self) -> None:
        """Block until current speech finishes (useful for testing or sequencing)."""
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join()

    # ── Single-text playback ──────────────────────────────────────────────────

    def _run_single(self, text: str) -> None:
        try:
            asyncio.run(self._synthesise_and_play(text))
        except Exception:
            log.error("TTS synthesis error", exc_info=True)
