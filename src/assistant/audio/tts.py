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
import io
import queue
import threading
from typing import Iterator

import sounddevice as sd
import soundfile as sf

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
        except Exception as exc:
            log.error(f"TTS error: {exc}", exc_info=True)

    async def _synthesise_and_play(self, text: str) -> None:
        mp3_bytes = await self._synthesise_mp3(text)
        if not mp3_bytes or self._stop_flag.is_set():
            return
        await self._play_mp3(mp3_bytes)

    # ── Streaming pipelined playback ──────────────────────────────────────────

    def _run_stream(self, sentence_iter: Iterator[str]) -> None:
        """
        Thread entry point for streaming TTS.

        Uses a thread-safe queue to pass synthesised audio chunks from the
        producer (synthesis) thread to the consumer (playback) thread.

        Queue size of 2 means we keep at most one sentence ahead in the buffer
        — enough to hide synthesis latency without wasting memory.
        """
        # Queue items: (audio_data: np.ndarray, sample_rate: int)
        # Sentinel: None signals the consumer to stop.
        audio_queue: queue.Queue = queue.Queue(maxsize=2)

        producer = threading.Thread(
            target=self._producer,
            args=(sentence_iter, audio_queue),
            daemon=True,
            name="tts-producer",
        )
        consumer = threading.Thread(
            target=self._consumer,
            args=(audio_queue,),
            daemon=True,
            name="tts-consumer",
        )

        producer.start()
        consumer.start()

        producer.join()
        consumer.join()

    def _producer(self, sentence_iter: Iterator[str], audio_queue: queue.Queue) -> None:
        """
        Producer: synthesise each sentence and put audio into the queue.

        Runs its own asyncio event loop so it can call the async Edge TTS API.
        """
        async def _run():
            for sentence in sentence_iter:
                if self._stop_flag.is_set():
                    break
                if not sentence.strip():
                    continue

                log.debug(f"TTS synthesising: {sentence[:60]!r}")
                mp3_bytes = await self._synthesise_mp3(sentence)

                if not mp3_bytes or self._stop_flag.is_set():
                    break

                buf = io.BytesIO(mp3_bytes)
                try:
                    audio_data, sample_rate = sf.read(buf, dtype="float32")
                    audio_queue.put((audio_data, sample_rate))  # blocks if queue is full
                except Exception as exc:
                    log.error(f"TTS decode error: {exc}", exc_info=True)

            audio_queue.put(None)  # sentinel — tells consumer we're done

        asyncio.run(_run())

    def _consumer(self, audio_queue: queue.Queue) -> None:
        """
        Consumer: play each audio chunk from the queue in order.

        Waits for the next chunk to be synthesised if the producer is still
        working. Each chunk plays to completion before the next starts,
        so sentences are always heard in order with no overlap.
        """
        while True:
            item = audio_queue.get()
            if item is None:
                break  # producer is done

            if self._stop_flag.is_set():
                # Drain remaining items so producer thread can exit
                while audio_queue.get() is not None:
                    pass
                break

            audio_data, sample_rate = item
            log.debug(
                f"TTS playing {len(audio_data) / sample_rate:.1f}s chunk "
                f"@ {sample_rate} Hz"
            )

            sd.play(audio_data, samplerate=sample_rate)

            # Poll every 50ms so we can honour a stop() call mid-playback
            while sd.get_stream().active:
                if self._stop_flag.is_set():
                    sd.stop()
                    return
                import time
                time.sleep(0.05)

            sd.wait()

    # ── Edge TTS synthesis (shared) ───────────────────────────────────────────

    async def _synthesise_mp3(self, text: str) -> bytes:
        """Fetch MP3 audio bytes from Microsoft Edge TTS."""
        import edge_tts  # noqa: PLC0415

        # Strip non-ASCII — Edge TTS English voices can't speak other scripts
        clean_text = text.encode("ascii", errors="ignore").decode("ascii").strip()
        if not clean_text:
            log.warning("TTS skipped — no speakable ASCII characters.")
            return b""

        log.debug(f"Edge TTS request: {clean_text[:60]!r}")
        communicate = edge_tts.Communicate(text=clean_text, voice=self._voice)

        chunks: list[bytes] = []
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
        except edge_tts.exceptions.NoAudioReceived:
            log.warning("Edge TTS: No audio received — skipping.")
            return b""

        mp3_bytes = b"".join(chunks)
        log.debug(f"Edge TTS returned {len(mp3_bytes):,} bytes.")
        return mp3_bytes

    async def _play_mp3(self, mp3_bytes: bytes) -> None:
        """Decode MP3 bytes and play through speakers (used by speak())."""
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

        sd.play(audio_data, samplerate=sample_rate)

        while sd.get_stream().active:
            if self._stop_flag.is_set():
                sd.stop()
                return
            await asyncio.sleep(0.05)

        sd.wait()
        log.debug("Playback complete.")


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
