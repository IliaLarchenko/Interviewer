import io
import wave

import numpy as np
import requests

from openai import OpenAI

from utils.errors import APIError, AudioConversionError
from typing import List, Dict, Optional, Generator, Tuple
import webrtcvad


def detect_voice(audio: np.ndarray, sample_rate: int = 48000, frame_duration: int = 30) -> bool:
    vad = webrtcvad.Vad()
    vad.set_mode(3)  # Aggressiveness mode: 0 (least aggressive) to 3 (most aggressive)

    # Convert numpy array to 16-bit PCM bytes
    audio_bytes = audio.tobytes()

    num_samples_per_frame = int(sample_rate * frame_duration / 1000)
    frames = [audio_bytes[i : i + num_samples_per_frame * 2] for i in range(0, len(audio_bytes), num_samples_per_frame * 2)]

    count_speech = 0
    for frame in frames:
        if len(frame) < num_samples_per_frame * 2:
            continue
        if vad.is_speech(frame, sample_rate):
            count_speech += 1
            if count_speech > 6:
                return True
    return False


class STTManager:
    def __init__(self, config):
        self.SAMPLE_RATE = 48000
        self.CHUNK_LENGTH = 5
        self.STEP_LENGTH = 3
        self.MAX_RELIABILITY_CUTOFF = self.CHUNK_LENGTH - 1

        self.config = config
        self.status = self.test_stt()
        self.streaming = self.test_streaming()

    def numpy_audio_to_bytes(self, audio_data: np.ndarray) -> bytes:
        """
        Convert a numpy array of audio data to bytes.

        :param audio_data: Numpy array containing audio data.
        :return: Bytes representation of the audio data.
        """
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

    def process_audio_chunk(self, audio: Tuple[int, np.ndarray], audio_buffer: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process streamed audio data to accumulate and transcribe with overlapping segments.

        :param audio: Tuple containing the sample rate and audio data as numpy array.
        :param audio_buffer: Current audio buffer as numpy array.
        :param transcript: Current transcript dictionary.
        :return: Updated transcript, updated audio buffer, and transcript text.
        """

        has_voice = detect_voice(audio[1])
        ended = len(audio[1]) % 24000 != 0

        if has_voice:
            audio_buffer = np.concatenate((audio_buffer, audio[1]))

        is_short = len(audio_buffer) / 48000 < 1.0

        if is_short or (has_voice and not ended):
            return audio_buffer, np.array([], dtype=np.int16)

        return np.array([], dtype=np.int16), audio_buffer

    def transcribe_audio(self, audio: np.ndarray, text) -> str:
        if len(audio) < 500:
            return text
        else:
            transcript = self.transcribe_numpy_array(audio, context=text)
            return text + " " + transcript

    def speech_to_text_stream(self, audio: bytes) -> List[Dict[str, str]]:
        """
        Convert speech to text from a byte stream using streaming.

        :param audio: Bytes representation of audio data.
        :return: List of dictionaries containing transcribed words and their timestamps.
        """
        if self.config.stt.type == "HF_API":
            raise APIError("STT Error: Streaming not supported for this STT type")
        try:
            data = ("temp.wav", audio, "audio/wav")
            client = OpenAI(base_url=self.config.stt.url, api_key=self.config.stt.key)
            transcription = client.audio.transcriptions.create(
                model=self.config.stt.name, file=data, response_format="verbose_json", timestamp_granularities=["word"]
            )
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"STT Error: Unexpected error: {e}")
        return transcription.words

    def merge_transcript(self, transcript: Dict, new_transcript: List[Dict[str, str]]) -> Dict:
        """
        Merge new transcript data with the existing transcript.

        :param transcript: Existing transcript dictionary.
        :param new_transcript: New transcript data to merge.
        :return: Updated transcript dictionary.
        """
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

    def transcribe_numpy_array(self, audio: np.ndarray, context: Optional[str] = None) -> str:
        """
        Convert speech to text from a full audio segment.

        :param audio: Tuple containing the sample rate and audio data as numpy array.
        :return: Transcribed text.
        """
        audio_bytes = self.numpy_audio_to_bytes(audio)
        try:
            if self.config.stt.type == "OPENAI_API":
                data = ("temp.wav", audio_bytes, "audio/wav")
                client = OpenAI(base_url=self.config.stt.url, api_key=self.config.stt.key)
                transcription = client.audio.transcriptions.create(
                    model=self.config.stt.name, file=data, response_format="text", prompt=context
                )
            elif self.config.stt.type == "HF_API":
                headers = {"Authorization": "Bearer " + self.config.stt.key}
                response = requests.post(self.config.stt.url, headers=headers, data=audio_bytes)
                if response.status_code != 200:
                    error_details = response.json().get("error", "No error message provided")
                    raise APIError("STT Error: HF API error", status_code=response.status_code, details=error_details)
                transcription = response.json().get("text", None)
                if transcription is None:
                    raise APIError("STT Error: No transcription returned by HF API")
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"STT Error: Unexpected error: {e}")

        return transcription

    def test_stt(self) -> bool:
        """
        Test if the STT service is working correctly.

        :return: True if the STT service is working, False otherwise.
        """
        try:
            self.speech_to_text_full((48000, np.zeros(10000)))
            return True
        except:
            return False

    def test_streaming(self) -> bool:
        """
        Test if the STT streaming service is working correctly.

        :return: True if the STT streaming service is working, False otherwise.
        """
        try:
            self.speech_to_text_stream(self.numpy_audio_to_bytes(np.zeros(10000)))
            return True
        except:
            return False


class TTSManager:
    def __init__(self, config):
        self.config = config
        self.status = self.test_tts(stream=False)
        self.streaming = self.test_tts(stream=True) if self.status else False

    def test_tts(self, stream) -> bool:
        """
        Test if the TTS service is working correctly.
        :return: True if the TTS service is working, False otherwise.
        """
        try:
            list(self.read_text("Handshake", stream=stream))
            return True
        except:
            return False

    def read_text(self, text: str, stream: Optional[bool] = None) -> Generator[bytes, None, None]:
        """
        Convert text to speech and return the audio bytes, optionally streaming the response.
        :param text: Text to convert to speech.
        :param stream: Whether to use streaming or not.
        :return: Generator yielding chunks of audio bytes.
        """
        if stream is None:
            stream = self.streaming

        headers = {"Authorization": "Bearer " + self.config.tts.key}
        data = {"model": self.config.tts.name, "input": text, "voice": "alloy", "response_format": "opus"}

        try:
            if not stream:
                if self.config.tts.type == "OPENAI_API":
                    response = requests.post(self.config.tts.url + "/audio/speech", headers=headers, json=data)
                elif self.config.tts.type == "HF_API":
                    response = requests.post(self.config.tts.url, headers=headers, json={"inputs": text})

                if response.status_code != 200:
                    error_details = response.json().get("error", "No error message provided")
                    raise APIError(f"TTS Error: {self.config.tts.type} error", status_code=response.status_code, details=error_details)
                yield response.content
            else:
                if self.config.tts.type != "OPENAI_API":
                    raise APIError("TTS Error: Streaming not supported for this TTS type")

                with requests.post(self.config.tts.url + "/audio/speech", headers=headers, json=data, stream=True) as response:
                    if response.status_code != 200:
                        error_details = response.json().get("error", "No error message provided")
                        raise APIError("TTS Error: OPENAI API error", status_code=response.status_code, details=error_details)
                    yield from response.iter_content(chunk_size=1024)
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"TTS Error: Unexpected error: {e}")

    def read_last_message(self, chat_history: List[List[Optional[str]]]) -> Generator[bytes, None, None]:
        """
        Read the last message in the chat history and convert it to speech.
        :param chat_history: List of chat messages.
        :return: Generator yielding chunks of audio bytes.
        """
        if len(chat_history) > 0 and chat_history[-1][1]:
            yield from self.read_text(chat_history[-1][1])
