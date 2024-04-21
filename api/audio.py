import io
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

    def speech_to_text(self, audio, convert_to_bytes=True):
        if convert_to_bytes:
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

        return transcription


class TTSManager:
    def __init__(self, config):
        self.config = config

    def text_to_speech(self, text):
        try:
            if self.config.tts.type == "OPENAI_API":
                client = OpenAI(base_url=self.config.tts.url, api_key=self.config.tts.key)
                response = client.audio.speech.create(model=self.config.tts.name, voice="alloy", response_format="opus", input=text)
            elif self.config.tts.type == "HF_API":
                headers = {"Authorization": "Bearer " + self.config.tts.key}
                response = requests.post(self.config.tts.url, headers=headers, json={"inputs": text})
                if response.status_code != 200:
                    error_details = response.json().get("error", "No error message provided")
                    raise APIError("TTS Error: HF API error", status_code=response.status_code, details=error_details)
        except APIError as e:
            raise
        except Exception as e:
            raise APIError(f"TTS Error: Unexpected error: {e}")

        return response.content

    def read_last_message(self, chat_display):
        if chat_display:
            last_message = chat_display[-1][1]
            if last_message is not None:
                return self.text_to_speech(last_message)
        return None
