import io
import wave

import numpy as np
import requests

from openai import OpenAI

from utils.errors import APIError, AudioConversionError


class STTManager:
    def __init__(self, config):
        self.SAMPLE_RATE = 48000
        self.CHUNK_LENGTH = 5
        self.STEP_LENGTH = 3
        self.MAX_RELIABILITY_CUTOFF = self.CHUNK_LENGTH - 1

        self.config = config
        self.status = self.test_stt()
        self.streaming = self.test_streaming()

    def numpy_audio_to_bytes(self, audio_data):
        num_channels = 1
        sampwidth = 2

        buffer = io.BytesIO()
        try:
            with wave.open(buffer, "wb") as wf:
                wf.setnchannels(num_channels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(audio_data.tobytes())
        except Exception as e:
            raise AudioConversionError(f"Error converting numpy array to audio bytes: {e}")
        return buffer.getvalue()

    def process_audio_chunk(self, audio, audio_buffer, transcript):
        """Process streamed audio data to accumulate and transcribe with overlapping segments."""
        audio_buffer = np.concatenate((audio_buffer, audio[1]))

        if len(audio_buffer) >= self.SAMPLE_RATE * self.CHUNK_LENGTH or len(audio_buffer) % (self.SAMPLE_RATE // 2) != 0:
            audio_bytes = self.numpy_audio_to_bytes(audio_buffer[: self.SAMPLE_RATE * self.CHUNK_LENGTH])
            audio_buffer = audio_buffer[self.SAMPLE_RATE * self.STEP_LENGTH :]

            new_transcript = self.speech_to_text_stream(audio_bytes)
            transcript = self.merge_transcript(transcript, new_transcript)

        return transcript, audio_buffer, transcript["text"]

    def speech_to_text_stream(self, audio):
        if self.config.stt.type == "HF_API":
            raise APIError("STT Error: Streaming not supported for this STT type")
        try:
            data = ("temp.wav", audio, "audio/wav")
            client = OpenAI(base_url=self.config.stt.url, api_key=self.config.stt.key)
            transcription = client.audio.transcriptions.create(
                model=self.config.stt.name, file=data, response_format="verbose_json", timestamp_granularities=["word"]
            )
        except APIError as e:
            raise
        except Exception as e:
            raise APIError(f"STT Error: Unexpected error: {e}")
        return transcription.words

    def merge_transcript(self, transcript, new_transcript):
        cut_off = transcript["last_cutoff"]
        transcript["last_cutoff"] = self.MAX_RELIABILITY_CUTOFF - self.STEP_LENGTH

        transcript["words"] = transcript["words"][: len(transcript["words"]) - transcript["not_confirmed"]]

        transcript["not_confirmed"] = 0
        first_word = True

        for word_dict in new_transcript:
            if word_dict["start"] >= cut_off:
                if first_word:
                    if len(transcript["words"]) > 0 and transcript["words"][-1] == word_dict["word"]:
                        continue
                first_word = False
                transcript["words"].append(word_dict["word"])
                if word_dict["start"] > self.MAX_RELIABILITY_CUTOFF:
                    transcript["not_confirmed"] += 1
                else:
                    transcript["last_cutoff"] = max(1.0, word_dict["end"] - self.STEP_LENGTH)

        transcript["text"] = " ".join(transcript["words"])

        return transcript

    def speech_to_text_full(self, audio):
        audio = self.numpy_audio_to_bytes(audio[1])
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

    def test_stt(self):
        try:
            self.speech_to_text_full((48000, np.zeros(10000)))
            return True
        except:
            return False

    def test_streaming(self):
        try:
            self.speech_to_text_stream(self.numpy_audio_to_bytes(np.zeros(10000)))
            return True
        except:
            return False


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
                data = {"model": self.config.tts.name, "input": text, "voice": "alloy", "response_format": "opus", "speed": 1.5}
                response = requests.post(self.config.tts.url + "/audio/speech", headers=headers, json=data)
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
            with requests.post(self.config.tts.url + "/audio/speech", headers=headers, json=data, stream=True) as response:
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
