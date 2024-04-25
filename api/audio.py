import io
import os
import wave

import requests

from openai import OpenAI

from utils.errors import APIError, AudioConversionError


def numpy_audio_to_bytes(audio_data):
    sample_rate = 44100
    num_channels = 1
    sampwidth = 2

    buffer = io.BytesIO()
    try:
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
    except Exception as e:
        raise AudioConversionError(f"Error converting numpy array to audio bytes: {e}")
    return buffer.getvalue()


class STTManager:
    def __init__(self, config):
        self.config = config
        self.streaming = os.getenv("STREAMING", False)

    def speech_to_text(self, audio, chat_display):
        audio = numpy_audio_to_bytes(audio[1])
        try:
            if self.config.stt.type == "OPENAI_API":
                data = ("temp.wav", audio, "audio/wav")
                client = OpenAI(base_url=self.config.stt.url, api_key=self.config.stt.key)
                transcription = client.audio.transcriptions.create(model=self.config.stt.name, file=data, response_format="text")
            elif self.config.stt.type == "HF_API":
                headers = {"Authorization": "Bearer " + self.config.stt.key}
                response = requests.post(self.config.stt.url, headers=headers, data=audio)
                if response.status_code != 200:
                    error_details = response.json().get("error", "No error message provided")
                    raise APIError("STT Error: HF API error", status_code=response.status_code, details=error_details)
                transcription = response.json().get("text", None)
                if transcription is None:
                    raise APIError("STT Error: No transcription returned by HF API")
        except APIError as e:
            raise
        except Exception as e:
            raise APIError(f"STT Error: Unexpected error: {e}")

        chat_display.append([transcription, None])
        return chat_display


class TTSManager:
    def test_tts(self):
        try:
            self.read_text("Handshake")
            return True
        except:
            return False

    def test_tts_stream(self):
        try:
            for _ in self.read_text_stream("Handshake"):
                pass
            return True
        except:
            return False

    def __init__(self, config):
        self.config = config
        self.status = self.test_tts()
        if self.status:
            self.streaming = self.test_tts_stream()
        else:
            self.streaming = False
        if self.streaming:
            self.read_last_message = self.rlm_stream
        else:
            self.read_last_message = self.rlm

    def read_text(self, text):
        headers = {"Authorization": "Bearer " + self.config.tts.key}
        try:
            if self.config.tts.type == "OPENAI_API":
                data = {"model": self.config.tts.name, "input": text, "voice": "alloy", "response_format": "opus"}
                response = requests.post(self.config.tts.url, headers=headers, json=data)
            elif self.config.tts.type == "HF_API":
                response = requests.post(self.config.tts.url, headers=headers, json={"inputs": text})
            if response.status_code != 200:
                error_details = response.json().get("error", "No error message provided")
                raise APIError(f"TTS Error: {self.config.tts.type} error", status_code=response.status_code, details=error_details)
        except APIError as e:
            raise
        except Exception as e:
            raise APIError(f"TTS Error: Unexpected error: {e}")

        return response.content

    def read_text_stream(self, text):
        if self.config.tts.type not in ["OPENAI_API"]:
            raise APIError("TTS Error: Streaming not supported for this TTS type")
        headers = {"Authorization": "Bearer " + self.config.tts.key}
        data = {"model": self.config.tts.name, "input": text, "voice": "alloy", "response_format": "opus"}

        try:
            with requests.post(self.config.tts.url, headers=headers, json=data, stream=True) as response:
                if response.status_code != 200:
                    error_details = response.json().get("error", "No error message provided")
                    raise APIError("TTS Error: OPENAI API error", status_code=response.status_code, details=error_details)
                else:
                    yield from response.iter_content(chunk_size=1024)
        except StopIteration:
            pass
        except APIError as e:
            raise
        except Exception as e:
            raise APIError(f"TTS Error: Unexpected error: {e}")

    def rlm(self, chat_history):
        if len(chat_history) > 0 and chat_history[-1][1]:
            return self.read_text(chat_history[-1][1])

    def rlm_stream(self, chat_history):
        if len(chat_history) > 0 and chat_history[-1][1]:
            yield from self.read_text_stream(chat_history[-1][1])
