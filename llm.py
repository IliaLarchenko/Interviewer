import json
import os

from openai import OpenAI

try:
    with open(".env") as file:
        for line in file:
            key, value = line.strip().split("=", 1)
            os.environ[key] = value
except FileNotFoundError:
    pass

client = OpenAI()


def init_bot(problem=""):
    prompt_system = (
        "You are ChatGPT acting as a coding round interviewer for a big-tech company. "
        "You are very strict. You don't give any hints until candidate is stuck or asks for it. "
        "If a candidate made a mistake let them find and debug it themselves. "
        "If a solution can be improved let candidate figure it out, you can ask directional questions but delay giving hints. "
        "For each version of solution ask candidate about time and space complexity. "
        "Strive to get the most optimal solution possible. "
        "Always return the answer in json format with 2 fields: reply_to_candidate and hidden_note. "
        "reply_to_candidate: the answer that will be shown to the candidate. "
        "hidden_note: the concise hidden note that is not visible to the candidate but will be useful for final grading and feedback, "
        "it can contain short code snippets, errors found, things to pay attention to. "
        "'reply_to_candidate' can not be empty, 'hidden_note' can be empty if there is no new important information to note. "
        "When the interview is finished and you don't have any more questions provide a very detailed feedback. "
        "Don't wait for the candidate to ask for feedback, provide it as soon as you don't have any more question or if you see that the candidate can't solve the problem at all. "
        "Provide detailed feedback using all the notes, mentioning not only the final solution but all issues and mistakes made during the interview. "
    )

    chat_history = [
        {"role": "system", "content": prompt_system},
        {"role": "system", "content": f"The candidate is solving the following problem: {problem}"},
    ]

    return chat_history


def get_problem(requirements="", client=client):
    prompt_system = "You are ChatGPT acting as a coding round interviewer for a big-tech company. "
    prompt_start = "Generate a coding problem that is expected to be solvable within 30 minutes. " "Follow the additional instructions: "
    prompt_end = (
        "Please provide the problem statement, example inputs and outputs, and any special constraints."
        "Return the results in nicely formatted markdown."
    )
    full_prompt = f"{prompt_start} {requirements} {prompt_end}"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": full_prompt},
        ],
    )

    question = response.choices[0].message.content.strip()
    chat_history = init_bot(question)

    return question, chat_history


def send_request(code, previous_code, message, chat_history, chat_display, client=client):
    if code != previous_code:
        chat_history.append({"role": "user", "content": f"My latest code: {code}"})
    chat_history.append({"role": "user", "content": message})

    response = client.chat.completions.create(model="gpt-3.5-turbo", response_format={"type": "json_object"}, messages=chat_history)

    json_reply = response.choices[0].message.content.strip()

    try:
        data = json.loads(json_reply)
        reply = data["reply_to_candidate"]
    except json.JSONDecodeError as e:
        print("Failed to decode JSON:", str(e))

    chat_history.append({"role": "assistant", "content": json_reply})

    chat_display.append([message, str(reply)])

    return chat_history, chat_display, "", code
