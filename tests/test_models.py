import pytest

from api.audio import STTManager, TTSManager
from api.llm import LLMManager
from utils.config import Config

# Simple placeholder tests so far
# TODO: add more tests including LLM based


@pytest.fixture
def app_config():
    return Config()


def test_llm_connection(app_config):
    llm = LLMManager(app_config, {})
    status = llm.status
    streaming = llm.streaming
    assert status, "LLM connection failed - status check failed"
    assert streaming, "LLM streaming failed - streaming check failed"


def test_stt_connection(app_config):
    stt = STTManager(app_config)
    status = stt.status
    streaming = stt.streaming
    assert status, "STT connection failed - status check failed"
    assert streaming, "STT streaming failed - streaming check failed"


def test_tts_connection(app_config):
    tts = TTSManager(app_config)
    status = tts.status
    streaming = tts.streaming
    assert status, "TTS connection failed - status check failed"
    assert streaming, "TTS streaming failed - streaming check failed"
