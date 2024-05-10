import os

from dotenv import load_dotenv


class ServiceConfig:
    def __init__(self, url_var, type_var, name_var):
        self.url = os.getenv(url_var)
        self.type = os.getenv(type_var)
        self.name = os.getenv(name_var)
        self.key = os.getenv(f"{self.type}_KEY")


class Config:
    def __init__(self):
        load_dotenv(override=True)
        self.llm = ServiceConfig("LLM_URL", "LLM_TYPE", "LLM_NAME")
        self.stt = ServiceConfig("STT_URL", "STT_TYPE", "STT_NAME")
        self.tts = ServiceConfig("TTS_URL", "TTS_TYPE", "TTS_NAME")
