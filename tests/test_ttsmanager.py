import pytest
from unittest.mock import patch, Mock
from api.audio import TTSManager, APIError


class TestTTSManager:

    def setup_method(self):
        self.config = Mock()
        self.config.tts.key = "test-key"
        self.config.tts.url = "https://api.example.com"
        self.config.tts.name = "test-tts-model"
        self.config.tts.type = "OPENAI_API"
        self.tts_manager = TTSManager(self.config)

    @patch("requests.post")
    @pytest.mark.parametrize("stream", [False, True])
    def test_read_text(self, mock_post, stream):
        self.tts_manager.streaming = stream
        if stream:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_content = Mock(return_value=[b"audio-bytes-part1", b"audio-bytes-part2"])
            mock_post.return_value.__enter__ = Mock(return_value=mock_response)
            mock_post.return_value.__exit__ = Mock(return_value=None)

            result = list(self.tts_manager.read_text("Hello, world!"))
            assert result == [b"audio-bytes-part1", b"audio-bytes-part2"]
        else:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"audio-bytes"
            mock_post.return_value = mock_response

            result = list(self.tts_manager.read_text("Hello, world!"))
            assert result == [b"audio-bytes"]

    @patch("requests.post")
    @pytest.mark.parametrize("stream", [False, True])
    def test_read_text_error(self, mock_post, stream):
        self.tts_manager.streaming = stream
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_post.return_value.__enter__ = Mock(return_value=mock_response)
        mock_post.return_value.__exit__ = Mock(return_value=None)

        with pytest.raises(APIError):
            list(self.tts_manager.read_text("Hello, world!"))

    @patch("requests.post")
    @pytest.mark.parametrize("stream", [False, True])
    def test_read_last_message(self, mock_post, stream):
        self.tts_manager.streaming = stream
        chat_history = [["user", "Hello, world!"]]
        if stream:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_content = Mock(return_value=[b"audio-bytes-part1", b"audio-bytes-part2"])
            mock_post.return_value.__enter__ = Mock(return_value=mock_response)
            mock_post.return_value.__exit__ = Mock(return_value=None)

            result = list(self.tts_manager.read_last_message(chat_history))
            assert result == [b"audio-bytes-part1", b"audio-bytes-part2"]
        else:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"audio-bytes"
            mock_post.return_value = mock_response

            result = list(self.tts_manager.read_last_message(chat_history))
            assert result == [b"audio-bytes"]

    @patch("requests.post")
    @pytest.mark.parametrize("stream", [False, True])
    def test_read_last_message_error(self, mock_post, stream):
        self.tts_manager.streaming = stream
        chat_history = [["user", "Hello, world!"]]
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_post.return_value.__enter__ = Mock(return_value=mock_response)
        mock_post.return_value.__exit__ = Mock(return_value=None)

        with pytest.raises(APIError):
            list(self.tts_manager.read_last_message(chat_history))
