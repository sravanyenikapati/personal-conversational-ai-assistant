"""
Sentence splitter for streaming AI responses.

Accumulates streamed text tokens and yields complete sentences so TTS
can start speaking the first sentence while the AI is still generating
the rest of the response.

This is the key to low-latency voice: instead of waiting for the full
response (3-8s), the user hears the first sentence within ~0.5s of the
AI starting to generate.

Usage:
    splitter = SentenceSplitter()
    for chunk in ai_stream:
        for sentence in splitter.feed(chunk):
            tts.speak(sentence)     # starts playing immediately
    remainder = splitter.flush()    # catch any trailing text
    if remainder:
        tts.speak(remainder)
"""

from __future__ import annotations

import re

# Matches a sentence boundary: sentence-ending punctuation followed by
# whitespace OR end of string. Uses lookbehind so the punctuation is
# kept with the sentence (not consumed by the split).
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[.!?])$")


class SentenceSplitter:
    """
    Accumulates streamed text chunks and yields complete sentences.

    Designed for AI streaming APIs where text arrives as small tokens
    (sometimes a single character). Buffers until a sentence boundary is
    found, then yields the complete sentence so TTS can start speaking
    while the AI generates the rest of the response.
    """

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str) -> list[str]:
        """
        Add a streamed text chunk. Returns any complete sentences found.

        Most calls return an empty list. A sentence is returned whenever a
        sentence-ending punctuation mark (. ! ?) followed by whitespace or
        end-of-string is detected.

        Args:
            chunk: A text token from the streaming AI response.

        Returns:
            A list of complete sentence strings (usually empty or one item).
        """
        self._buffer += chunk
        sentences: list[str] = []

        while True:
            match = _SENTENCE_END.search(self._buffer)
            if not match:
                break
            sentence = self._buffer[: match.start() + 1].strip()
            if sentence:
                sentences.append(sentence)
            self._buffer = self._buffer[match.end() :]

        return sentences

    def flush(self) -> str:
        """
        Return any text remaining in the buffer after the stream ends.

        Always call this after the AI stream is exhausted to catch responses
        that don't end with a sentence-ending punctuation mark.

        Returns:
            Remaining buffered text, or "" if the buffer is empty.
        """
        remainder = self._buffer.strip()
        self._buffer = ""
        return remainder

    def reset(self) -> None:
        """Clear the buffer (call between separate responses)."""
        self._buffer = ""

    def __repr__(self) -> str:
        return f"SentenceSplitter(buffer={self._buffer!r})"
