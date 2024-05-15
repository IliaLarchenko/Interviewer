from dotenv import load_dotenv
import os
from typing import Optional


class ServiceConfig:
    def __init__(self, url_var: str, type_var: str, name_var: str):
        """
        Initialize the ServiceConfig with environment variables.

        :param url_var: Environment variable for the service URL.
        :param type_var: Environment variable for the service type.
        :param name_var: Environment variable for the service name.
        """
        self.url: Optional[str] = os.getenv(url_var)
        self.type: Optional[str] = os.getenv(type_var)
        self.name: Optional[str] = os.getenv(name_var)
        self.key: Optional[str] = os.getenv(f"{self.type}_KEY")


class Config:
    def __init__(self):
        """
        Load environment variables and initialize service configurations.
        """
        load_dotenv(override=True)
        self.llm: ServiceConfig = ServiceConfig("LLM_URL", "LLM_TYPE", "LLM_NAME")
        self.stt: ServiceConfig = ServiceConfig("STT_URL", "STT_TYPE", "STT_NAME")
        self.tts: ServiceConfig = ServiceConfig("TTS_URL", "TTS_TYPE", "TTS_NAME")
