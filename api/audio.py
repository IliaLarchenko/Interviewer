import io
import wave

import requests

from openai import OpenAI


def numpy_audio_to_bytes(audio_data):
    sample_rate = 44100
    num_channels = 1
    sampwidth = 2

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
    return buffer.getvalue()


class STTManager:
    def __init__(self, config):
        self.config = config

    def speech_to_text(self, audio, convert_to_bytes=True):
        if convert_to_bytes:
            audio = numpy_audio_to_bytes(audio[1])

        if self.config.stt.type == "OPENAI_API":
            data = ("temp.wav", audio, "audio/wav")
            client = OpenAI(base_url=self.config.stt.url, api_key=self.config.stt.key)
            transcription = client.audio.transcriptions.create(model=self.config.stt.name, file=data, response_format="text")
        elif self.config.stt.type == "HF_API":
            headers = {"Authorization": "Bearer " + self.config.stt.key}
            transcription = requests.post(self.config.stt.url, headers=headers, data=audio)
            transcription = transcription.json()["text"]

        return transcription


class TTSManager:
    def __init__(self, config):
        self.config = config

    def text_to_speech(self, text):
        if self.config.tts.type == "OPENAI_API":
            client = OpenAI(base_url=self.config.tts.url, api_key=self.config.tts.key)
            response = client.audio.speech.create(model=self.config.tts.name, voice="alloy", response_format="opus", input=text)
        elif self.config.tts.type == "HF_API":
            headers = {"Authorization": "Bearer " + self.config.tts.key}
            response = requests.post(self.config.tts.url, headers=headers)

        return response.content

    def read_last_message(self, chat_display):
        if chat_display:
            last_message = chat_display[-1][1]  # Assuming the message is stored at index 1 of the last tuple/list in chat_display
            if last_message is not None:
                return self.text_to_speech(last_message)
        return None
