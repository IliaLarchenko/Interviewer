import json
import os

import requests

from dotenv import load_dotenv
from openai import OpenAI

from audio import numpy_audio_to_bytes
from config import LLM_NAME, LLM_TYPE, LLM_URL, STT_NAME, STT_TYPE, STT_URL, TTS_NAME, TTS_TYPE, TTS_URL
from prompts import coding_interviewer_prompt, grading_feedback_prompt, problem_generation_prompt

load_dotenv()

client_LLM = OpenAI(base_url=LLM_URL, api_key=os.getenv(f"{LLM_TYPE}_KEY"))


def init_bot(problem=""):
    chat_history = [
        {"role": "system", "content": coding_interviewer_prompt},
        {"role": "system", "content": f"The candidate is solving the following problem: {problem}"},
    ]
    return chat_history


def get_problem(requirements, difficulty, topic, client=client_LLM):
    full_prompt = (
        f"Create a {difficulty} {topic} coding problem. "
        f"Additional requirements: {requirements}. "
        "The problem should be clearly stated, well-formatted, and solvable within 30 minutes. "
        "Ensure the problem varies each time to provide a wide range of challenges."
    )
    response = client.chat.completions.create(
        model=LLM_NAME,
        messages=[
            {"role": "system", "content": problem_generation_prompt},
            {"role": "user", "content": full_prompt},
        ],
        temperature=1.0,  # Adjusted for a balance between creativity and coherency
    )
    question = response.choices[0].message.content.strip()
    chat_history = init_bot(question)
    return question, chat_history


def end_interview(problem_description, chat_history, client=client_LLM):
    if not chat_history or len(chat_history) <= 2:
        return "No interview content available to review."

    transcript = []
    for message in chat_history[1:]:
        role = message["role"]
        content = f"{role.capitalize()}: {message['content']}"
        transcript.append(content)

    response = client.chat.completions.create(
        model=LLM_NAME,
        messages=[
            {"role": "system", "content": grading_feedback_prompt},
            {"role": "user", "content": f"The original problem to solve: {problem_description}"},
            {"role": "user", "content": "\n\n".join(transcript)},
            {"role": "user", "content": "Grade the interview based on the transcript provided and give feedback."},
        ],
        temperature=0.5,
    )
    feedback = response.choices[0].message.content.strip()
    return feedback


def send_request(code, previous_code, message, chat_history, chat_display, client=client_LLM):
    if code != previous_code:
        chat_history.append({"role": "user", "content": f"My latest code:\n{code}"})
    chat_history.append({"role": "user", "content": message})

    response = client.chat.completions.create(model=LLM_NAME, messages=chat_history)

    reply = response.choices[0].message.content.strip()

    chat_history.append({"role": "assistant", "content": reply})
    chat_display.append([message, reply])

    return chat_history, chat_display, "", code


def speech_to_text(audio):
    assert STT_TYPE in ["OPENAI_API", "HF_API"]

    if STT_TYPE == "OPENAI_API":
        data = ("temp.wav", numpy_audio_to_bytes(audio[1]), "audio/wav")
        client = OpenAI(base_url=STT_URL, api_key=os.getenv(f"{STT_TYPE}_KEY"))
        transcription = client.audio.transcriptions.create(model=STT_NAME, file=data, response_format="text")
    elif STT_TYPE == "HF_API":
        headers = {"Authorization": "Bearer " + os.getenv(f"{STT_TYPE}_KEY")}
        transcription = requests.post(STT_URL, headers=headers, data=numpy_audio_to_bytes(audio[1]))
        transcription = transcription.json()["text"]

    return transcription


def text_to_speech(text):
    assert TTS_TYPE in ["OPENAI_API", "HF_API"]

    if TTS_TYPE == "OPENAI_API":
        client = OpenAI(base_url=TTS_URL, api_key=os.getenv(f"{TTS_TYPE}_KEY"))
        response = client.audio.speech.create(model=TTS_NAME, voice="alloy", input=text)
    elif TTS_TYPE == "HF_API":
        headers = {"Authorization": "Bearer " + os.getenv(f"{STT_TYPE}_KEY")}
        response = requests.post(TTS_URL, headers=headers)

    audio = response.content
    return audio


def read_last_message(chat_display):
    last_message = chat_display[-1][1]
    if last_message is not None:
        audio = text_to_speech(last_message)
        return audio
    return None
