"""
Tests for audio modules (STT + TTS).

Audio hardware is mocked — these tests run in CI with no microphone or speakers.
"""

from unittest.mock import AsyncMock, MagicMock, patch


class TestTextToSpeech:
    @patch("assistant.audio.tts.edge_tts")
    def test_speak_does_not_raise(self, mock_edge_tts):
        """TTS.speak() should not raise even if edge_tts fails."""
        from assistant.audio.tts import TextToSpeech

        mock_communicate = MagicMock()
        mock_communicate.stream = AsyncMock(return_value=iter([]))
        mock_edge_tts.Communicate.return_value = mock_communicate

        tts = TextToSpeech()
        # speak() is non-blocking — should not raise
        tts.speak("Hello there")

    @patch("assistant.audio.tts.edge_tts")
    def test_speak_empty_string_is_noop(self, mock_edge_tts):
        """TTS.speak() with empty string should do nothing."""
        from assistant.audio.tts import TextToSpeech

        tts = TextToSpeech()
        tts.speak("")
        # edge_tts.Communicate should never be called for empty input
        mock_edge_tts.Communicate.assert_not_called()

    def test_stop_does_not_raise_when_idle(self):
        """TTS.stop() should be safe to call even when nothing is playing."""
        from assistant.audio.tts import TextToSpeech

        tts = TextToSpeech()
        tts.stop()  # should not raise


class TestSpeechToText:
    def test_stt_initialises_with_correct_engine(self):
        """STT should pick up the engine from settings."""
        from assistant.audio.stt import SpeechToText
        from assistant.config import STTEngine

        stt = SpeechToText()
        assert stt._engine in (STTEngine.WHISPER_API, STTEngine.WHISPER_LOCAL)

    @patch("assistant.audio.stt.pyaudio.PyAudio")
    @patch("assistant.audio.stt.SpeechToText._whisper_api", return_value="hello world")
    def test_transcribe_returns_text(self, mock_whisper, mock_pyaudio):
        """transcribe() should return the string from the STT engine."""
        from assistant.audio.stt import SpeechToText

        stt = SpeechToText()
        # _record is the heavy part — mock it to return fake WAV bytes
        with patch.object(stt, "_record", return_value=b"fake-wav-bytes"):
            result = stt.transcribe()
        assert result == "hello world"

    @patch("assistant.audio.stt.SpeechToText._record", return_value=None)
    def test_transcribe_returns_empty_when_no_audio(self, mock_record):
        """transcribe() should return '' if no audio was captured."""
        from assistant.audio.stt import SpeechToText

        stt = SpeechToText()
        result = stt.transcribe()
        assert result == ""
