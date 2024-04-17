import io
import wave


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
