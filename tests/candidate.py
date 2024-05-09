import json
import os
import random
import string
import time

from collections import defaultdict

from dotenv import load_dotenv
from openai import OpenAI

from api.llm import LLMManager
from config import config
from resources.data import fixed_messages, topic_lists
from resources.prompts import prompts
from tests.tessting_prompts import candidate_prompt

load_dotenv()


def complete_interview(interview_type, exp_name, requirements="", difficulty="", topic="", model="gpt-3.5-turbo"):
    client = OpenAI()
    llm = LLMManager(config, prompts)
    llm_name = config.llm.name

    # Select a random topic or difficulty if not provided
    topic = topic or random.choice(topic_lists[interview_type])
    difficulty = difficulty or random.choice(["easy", "medium", "hard"])

    problem_statement_text = llm.get_problem_full(requirements, difficulty, topic, interview_type)

    interview_data = defaultdict(
        lambda: None,
        {
            "interviewer_llm": llm_name,
            "candidate_llm": model,
            "inputs": {
                "interview_type": interview_type,
                "difficulty": difficulty,
                "topic": topic,
                "requirements": requirements,
            },
            "problem_statement": problem_statement_text,
            "transcript": [],
            "feedback": None,
            "average_response_time_seconds": 0,
        },
    )

    # Initialize interviewer and candidate messages
    messages_interviewer = llm.init_bot(problem_statement_text, interview_type)
    chat_display = [[None, fixed_messages["start"]]]

    messages_candidate = [
        {"role": "system", "content": candidate_prompt},
        {"role": "user", "content": f"Your problem: {problem_statement_text}"},
        {"role": "user", "content": chat_display[-1][1]},
    ]

    response_times = []
    previous_code = ""

    for _ in range(30):
        response = client.chat.completions.create(
            model=model, messages=messages_candidate, temperature=1, response_format={"type": "json_object"}
        )
        response_json = json.loads(response.choices[0].message.content)

        code = response_json.get("code", "")
        candidate_message = response_json.get("message", "")

        if not code and not candidate_message:
            print("No message or code in response")
            continue

        messages_candidate.append({"role": "assistant", "content": response.choices[0].message.content})

        if code:
            interview_data["transcript"].append(f"CANDIDATE CODE: {code}")
        elif candidate_message:
            interview_data["transcript"].append(f"CANDIDATE MESSAGE: {candidate_message}")

        chat_display.append([candidate_message, None])

        # Check if the interview should finish
        if response_json.get("finished") and not response_json.get("question"):
            break

        send_time = time.time()
        messages_interviewer, chat_display, previous_code = llm.send_request_full(code, previous_code, messages_interviewer, chat_display)
        response_times.append(time.time() - send_time)

        messages_candidate.append({"role": "user", "content": chat_display[-1][1]})
        interview_data["transcript"].append(f"INTERVIEWER MESSAGE: {chat_display[-1][1]}")

    interview_data["feedback"] = llm.end_interview_full(problem_statement_text, messages_interviewer, interview_type)
    interview_data["average_response_time_seconds"] = round(sum(response_times) / len(response_times), 2) if response_times else 0

    current_time = time.strftime("%Y%m%d-%H%M%S")
    random_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    file_path = os.path.join("records", exp_name, f"{current_time}-{random_suffix}.json")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w") as file:
        json.dump(interview_data, file, indent=4)

    return file_path, interview_data
