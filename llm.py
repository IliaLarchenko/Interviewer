import json

from dotenv import load_dotenv
from openai import OpenAI

from prompts import coding_interviewer_prompt, grading_feedback_prompt

load_dotenv()
client = OpenAI()


def init_bot(problem=""):
    chat_history = [
        {"role": "system", "content": coding_interviewer_prompt},
        {"role": "system", "content": f"The candidate is solving the following problem: {problem}"},
    ]
    return chat_history


def get_problem(requirements, difficulty, topic, model, client=client):
    prompt_system = "You are ChatGPT acting as a coding round interviewer for a big-tech company. "
    full_prompt = f"Generate a {difficulty} {topic} problem in. Follow additional requirements: {requirements}. The problem should be solvable within 30 minutes."
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": full_prompt},
        ],
    )
    question = response.choices[0].message.content.strip()
    chat_history = init_bot(question)
    return question, chat_history


def end_interview(chat_history, model, client=client):
    transcript = []
    for message in chat_history[1:]:
        role = message["role"]
        content = f"{role.capitalize()}: {message['content']}"
        transcript.append(content)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": grading_feedback_prompt},
            {"role": "user", "content": "Interview transcript:" + "\n\n".join(transcript)},
            {"role": "user", "content": "Grade the interview based on the transcript provided and give a feedback."},
        ],
    )
    feedback = response.choices[0].message.content.strip()
    return feedback


def send_request(code, previous_code, message, chat_history, chat_display, model, client=client):
    if code != previous_code:
        chat_history.append({"role": "user", "content": f"My latest code: {code}"})
    chat_history.append({"role": "user", "content": message})

    response = client.chat.completions.create(model=model, response_format={"type": "json_object"}, messages=chat_history)

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
