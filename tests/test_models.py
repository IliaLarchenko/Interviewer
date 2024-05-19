import pytest

from api.audio import STTManager, TTSManager
from api.llm import LLMManager
from utils.config import Config


@pytest.fixture
def app_config():
    return Config()


def test_llm_connection(app_config: Config):
    """
    Test the connection and streaming capability of the LLM.

    :param app_config: Configuration object.
    """
    llm = LLMManager(app_config, {})
    assert llm.status, "LLM connection failed - status check failed"
    assert llm.streaming, "LLM streaming failed - streaming check failed"


def test_stt_connection(app_config: Config):
    """
    Test the connection and streaming capability of the STT.

    :param app_config: Configuration object.
    """
    stt = STTManager(app_config)
    status = stt.status
    streaming = stt.streaming
    assert status, "STT connection failed - status check failed"
    assert streaming, "STT streaming failed - streaming check failed"


def test_tts_connection(app_config: Config):
    """
    Test the connection and streaming capability of the TTS.

    :param app_config: Configuration object.
    """
    tts = TTSManager(app_config)
    status = tts.status
    streaming = tts.streaming
    assert status, "TTS connection failed - status check failed"
    assert streaming, "TTS streaming failed - streaming check failed"
