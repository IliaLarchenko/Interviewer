import io
import wave
import numpy as np
import requests
from openai import OpenAI
import webrtcvad
from transformers import pipeline
from typing import List, Optional, Generator, Tuple, Any
from utils.errors import APIError, AudioConversionError

SAMPLE_RATE: int = 48000
FRAME_DURATION: int = 30


def detect_voice(audio: np.ndarray, sample_rate: int = SAMPLE_RATE, frame_duration: int = FRAME_DURATION) -> bool:
    """
    Detect voice activity in the given audio data.

    Args:
        audio (np.ndarray): Audio data as a numpy array.
        sample_rate (int): Sample rate of the audio. Defaults to SAMPLE_RATE.
        frame_duration (int): Duration of each frame in milliseconds. Defaults to FRAME_DURATION.

    Returns:
        bool: True if voice activity is detected, False otherwise.
    """
    vad = webrtcvad.Vad(3)  # Aggressiveness mode: 3 (most aggressive)
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
    """Manages speech-to-text operations."""

    def __init__(self, config: Any):
        """
        Initialize the STTManager.

        Args:
            config (Any): Configuration object containing STT settings.
        """
        self.config = config
        self.SAMPLE_RATE: int = SAMPLE_RATE
        self.CHUNK_LENGTH: int = 5
        self.STEP_LENGTH: int = 3
        self.MAX_RELIABILITY_CUTOFF: int = self.CHUNK_LENGTH - 1
        self.status: bool = self.test_stt()
        self.streaming: bool = self.status
        if config.stt.type == "HF_LOCAL":
            self.pipe = pipeline("automatic-speech-recognition", model=config.stt.name)

    def numpy_audio_to_bytes(self, audio_data: np.ndarray) -> bytes:
        """
        Convert numpy array audio data to bytes.

        Args:
            audio_data (np.ndarray): Audio data as a numpy array.

        Returns:
            bytes: Audio data as bytes.

        Raises:
            AudioConversionError: If there's an error during conversion.
        """
        buffer = io.BytesIO()
        try:
            with wave.open(buffer, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(audio_data.tobytes())
        except Exception as e:
            raise AudioConversionError(f"Error converting numpy array to audio bytes: {e}")
        return buffer.getvalue()

    def process_audio_chunk(self, audio: Tuple[int, np.ndarray], audio_buffer: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process an audio chunk and update the audio buffer.

        Args:
            audio (Tuple[int, np.ndarray]): Audio chunk data.
            audio_buffer (np.ndarray): Existing audio buffer.

        Returns:
            Tuple[np.ndarray, np.ndarray]: Updated audio buffer and processed audio.
        """
        has_voice = detect_voice(audio[1])
        ended = len(audio[1]) % 24000 != 0
        if has_voice:
            audio_buffer = np.concatenate((audio_buffer, audio[1]))
        is_short = len(audio_buffer) / self.SAMPLE_RATE < 1.0
        if is_short or (has_voice and not ended):
            return audio_buffer, np.array([], dtype=np.int16)
        return np.array([], dtype=np.int16), audio_buffer

    def transcribe_audio(self, audio: np.ndarray, text: str = "") -> str:
        """
        Transcribe audio data and append to existing text.

        Args:
            audio (np.ndarray): Audio data to transcribe.
            text (str): Existing text to append to. Defaults to empty string.

        Returns:
            str: Transcribed text appended to existing text.
        """
        if len(audio) < 500:
            return text
        transcript = self.transcribe_numpy_array(audio, context=text)

        return f"{text} {transcript}".strip()

    def transcribe_and_add_to_chat(self, audio: np.ndarray, chat: List[List[Optional[str]]]) -> List[List[Optional[str]]]:
        """
        Transcribe audio and add the result to the chat history.

        Args:
            audio (np.ndarray): Audio data to transcribe.
            chat (List[List[Optional[str]]]): Existing chat history.

        Returns:
            List[List[Optional[str]]]: Updated chat history with transcribed text.
        """
        text = self.transcribe_audio(audio)
        return self.add_to_chat(text, chat)

    def add_to_chat(self, text: str, chat: List[List[Optional[str]]]) -> List[List[Optional[str]]]:
        """
        Add text to the chat history.

        Args:
            text (str): Text to add to chat.
            chat (List[List[Optional[str]]]): Existing chat history.
            editable_chat (bool): Whether the chat is editable. Defaults to True.

        Returns:
            List[List[Optional[str]]]: Updated chat history.
        """
        if not text:
            return chat
        if not chat or chat[-1][0] is None:
            chat.append(["", None])
        chat[-1][0] = text
        return chat

    def transcribe_numpy_array(self, audio: np.ndarray, context: Optional[str] = None) -> str:
        """
        Transcribe audio data using the configured STT service.

        Args:
            audio (np.ndarray): Audio data as a numpy array.
            context (Optional[str]): Optional context for transcription.

        Returns:
            str: Transcribed text.

        Raises:
            APIError: If there's an unexpected error during transcription.
        """
        transcription_methods = {
            "OPENAI_API": self._transcribe_openai,
            "HF_API": self._transcribe_hf_api,
            "HF_LOCAL": self._transcribe_hf_local,
        }

        try:
            transcribe_method = transcription_methods.get(self.config.stt.type)
            if transcribe_method:
                return transcribe_method(audio, context)
            else:
                raise APIError(f"Unsupported STT type: {self.config.stt.type}")
        except Exception as e:
            raise APIError(f"STT Error: Unexpected error: {e}")

    def _transcribe_openai(self, audio: np.ndarray, context: Optional[str]) -> str:
        """
        Transcribe audio using OpenAI API.

        Args:
            audio (np.ndarray): Audio data as a numpy array.
            context (Optional[str]): Optional context for transcription.

        Returns:
            str: Transcribed text.
        """
        audio_bytes = self.numpy_audio_to_bytes(audio)
        data = ("temp.wav", audio_bytes, "audio/wav")
        client = OpenAI(base_url=self.config.stt.url, api_key=self.config.stt.key)
        return client.audio.transcriptions.create(model=self.config.stt.name, file=data, response_format="text", prompt=context)

    def _transcribe_hf_api(self, audio: np.ndarray, _context: Optional[str]) -> str:
        """
        Transcribe audio using Hugging Face API.

        Args:
            audio (np.ndarray): Audio data as a numpy array.
            _context (Optional[str]): Unused context parameter.

        Returns:
            str: Transcribed text.

        Raises:
            APIError: If there's an error in the API response.
        """
        audio_bytes = self.numpy_audio_to_bytes(audio)
        headers = {"Authorization": f"Bearer {self.config.stt.key}"}
        response = requests.post(self.config.stt.url, headers=headers, data=audio_bytes)
        if response.status_code != 200:
            error_details = response.json().get("error", "No error message provided")
            raise APIError("STT Error: HF API error", status_code=response.status_code, details=error_details)
        transcription = response.json().get("text")
        if transcription is None:
            raise APIError("STT Error: No transcription returned by HF API")
        return transcription

    def _transcribe_hf_local(self, audio: np.ndarray, _context: Optional[str]) -> str:
        """
        Transcribe audio using local Hugging Face model.

        Args:
            audio (np.ndarray): Audio data as a numpy array.
            _context (Optional[str]): Unused context parameter.

        Returns:
            str: Transcribed text.
        """
        result = self.pipe({"sampling_rate": self.SAMPLE_RATE, "raw": audio.astype(np.float32) / 32768.0})
        return result["text"]

    def test_stt(self) -> bool:
        """
        Test the STT functionality.

        Returns:
            bool: True if the test is successful, False otherwise.
        """
        try:
            self.transcribe_audio(np.zeros(10000))
            return True
        except:
            return False


class TTSManager:
    """Manages text-to-speech operations."""

    def __init__(self, config: Any):
        """
        Initialize the TTSManager.

        Args:
            config (Any): Configuration object containing TTS settings.
        """
        self.config = config
        self.SAMPLE_RATE: int = SAMPLE_RATE
        self.status: bool = self.test_tts(stream=False)
        self.streaming: bool = self.test_tts(stream=True) if self.status else False

    def test_tts(self, stream: bool) -> bool:
        """
        Test the TTS functionality.

        Args:
            stream (bool): Whether to test streaming TTS.

        Returns:
            bool: True if the test is successful, False otherwise.
        """
        try:
            list(self.read_text("Handshake", stream=stream))
            return True
        except:
            return False

    def read_text(self, text: str, stream: Optional[bool] = None) -> Generator[bytes, None, None]:
        """
        Convert text to speech using the configured TTS service.

        Args:
            text (str): Text to convert to speech.
            stream (Optional[bool]): Whether to stream the audio. Defaults to self.streaming if not provided.

        Yields:
            bytes: Audio data in bytes.

        Raises:
            APIError: If there's an unexpected error during text-to-speech conversion.
        """
        if not text:
            yield b""
            return

        stream = self.streaming if stream is None else stream

        headers = {"Authorization": f"Bearer {self.config.tts.key}"}
        data = {"model": self.config.tts.name, "input": text, "voice": "alloy", "response_format": "opus"}

        try:
            yield from self._read_text_stream(headers, data) if stream else self._read_text_non_stream(headers, data)
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"TTS Error: Unexpected error: {e}")

    def _read_text_non_stream(self, headers: dict, data: dict) -> Generator[bytes, None, None]:
        """
        Handle non-streaming TTS requests.

        Args:
            headers (dict): Request headers.
            data (dict): Request data.

        Yields:
            bytes: Audio data in bytes.

        Raises:
            APIError: If there's an error in the API response.
        """
        if self.config.tts.type == "OPENAI_API":
            url = f"{self.config.tts.url}/audio/speech"
        elif self.config.tts.type == "HF_API":
            url = self.config.tts.url
            data = {"inputs": data["input"]}
        else:
            raise APIError(f"TTS Error: Unsupported TTS type: {self.config.tts.type}")

        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            error_details = response.json().get("error", "No error message provided")
            raise APIError(f"TTS Error: {self.config.tts.type} error", status_code=response.status_code, details=error_details)
        yield response.content

    def _read_text_stream(self, headers: dict, data: dict) -> Generator[bytes, None, None]:
        """
        Handle streaming TTS requests.

        Args:
            headers (dict): Request headers.
            data (dict): Request data.

        Yields:
            bytes: Audio data in bytes.

        Raises:
            APIError: If there's an error in the API response or if streaming is not supported.
        """
        if self.config.tts.type != "OPENAI_API":
            raise APIError("TTS Error: Streaming not supported for this TTS type")

        url = f"{self.config.tts.url}/audio/speech"
        with requests.post(url, headers=headers, json=data, stream=True) as response:
            if response.status_code != 200:
                error_details = response.json().get("error", "No error message provided")
                raise APIError("TTS Error: OPENAI API error", status_code=response.status_code, details=error_details)
            yield from response.iter_content(chunk_size=1024)

    def read_last_message(self, chat_history: List[List[Optional[str]]]) -> Generator[bytes, None, None]:
        """
        Read the last message in the chat history.

        Args:
            chat_history (List[List[Optional[str]]]): Chat history.

        Yields:
            bytes: Audio data for the last message.
        """
        if chat_history and chat_history[-1][1]:
            yield from self.read_text(chat_history[-1][1])
