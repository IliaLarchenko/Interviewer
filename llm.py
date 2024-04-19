import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from audio import numpy_audio_to_bytes
from config import LLM_KEY_TYPE, LLM_NAME, LLM_URL, STT_KEY_TYPE, STT_NAME, STT_URL, TTS_KEY_TYPE, TTS_NAME, TTS_URL
from prompts import coding_interviewer_prompt, grading_feedback_prompt, problem_generation_prompt

load_dotenv()

client_LLM = OpenAI(base_url=LLM_URL, api_key=os.getenv(LLM_KEY_TYPE))
print(client_LLM.base_url)
client_STT = OpenAI(base_url=STT_URL, api_key=os.getenv(STT_KEY_TYPE))
client_TTS = OpenAI(base_url=TTS_URL, api_key=os.getenv(TTS_KEY_TYPE))


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

    response = client.chat.completions.create(model=LLM_NAME, response_format={"type": "json_object"}, messages=chat_history)

    json_reply = response.choices[0].message.content.strip()

    try:
        data = json.loads(json_reply)
        reply = data["reply_to_candidate"]
    except json.JSONDecodeError as e:
        print("Failed to decode JSON:", str(e))
        reply = "There was an error processing your request."

    chat_history.append({"role": "assistant", "content": json_reply})
    chat_display.append([message, str(reply)])

    return chat_history, chat_display, "", code


def speech_to_text(audio, client=client_STT):
    transcription = client.audio.transcriptions.create(
        model=STT_NAME, file=("temp.wav", numpy_audio_to_bytes(audio[1]), "audio/wav"), response_format="text"
    )
    return transcription


def text_to_speech(text, client=client_TTS):
    response = client.audio.speech.create(model=TTS_NAME, voice="alloy", input=text)
    return response.content


def read_last_message(chat_display):
    last_message = chat_display[-1][1]

    audio = text_to_speech(last_message)
    return audio
