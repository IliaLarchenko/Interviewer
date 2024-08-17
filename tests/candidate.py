import json
import os
import random
import string
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from openai import OpenAI
from api.llm import LLMManager
from utils.config import Config
from resources.data import fixed_messages, topic_lists
from resources.prompts import prompts
from tests.testing_prompts import candidate_prompt
from ui.coding import send_request


def complete_interview(
    interview_type: str,
    exp_name: str,
    llm_config: Optional[Config] = None,
    requirements: str = "",
    difficulty: str = "",
    topic: str = "",
    model: str = "gpt-4o-mini",
    pause: int = 0,
    mode: str = "normal",
    max_messages: Optional[int] = None,
) -> Tuple[str, Dict]:
    """
    Complete an interview and record the results with additional strange use cases.

    :param interview_type: Type of interview to complete.
    :param exp_name: Experiment name for file saving.
    :param llm_config: Optional LLM configuration.
    :param requirements: Additional requirements for the interview.
    :param difficulty: Difficulty level for the interview.
    :param topic: Topic for the interview.
    :param model: Model to use for the candidate.
    :param pause: Pause duration between requests to prevent rate limits.
    :param mode: Mode of operation ("normal", "empty", "gibberish", "repeat").
    :param max_messages: Maximum number of messages in the conversation.
    :return: Tuple containing the file path and interview data.
    """
    client = OpenAI(base_url="https://api.openai.com/v1")
    config = Config()
    if llm_config:
        config.llm = llm_config
    llm = LLMManager(config, prompts)
    llm_name = config.llm.name
    print(f"Starting evaluation interviewer LLM: {llm_name}, candidate LLM: {model}, interview type: {interview_type}")
    # Select a random topic or difficulty if not provided
    topic = topic or random.choice(topic_lists[interview_type])
    difficulty = difficulty or random.choice(["easy", "medium", "hard"])

    # Fix: Iterate over all elements and keep the last one
    problem_statement_text = None
    for text in llm.get_problem(requirements, difficulty, topic, interview_type):
        problem_statement_text = text

    if problem_statement_text is None:
        raise ValueError("Failed to get problem statement")

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

    if max_messages is None:
        max_messages = 25 if mode == "normal" else 5

    for _ in range(max_messages):
        code = ""
        if mode == "empty":
            candidate_message = ""
        elif mode == "gibberish":
            candidate_message = "".join(random.choices(string.ascii_letters + string.digits, k=50))
        elif mode == "repeat":
            candidate_message = chat_display[-1][1]
        else:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages_candidate,
                    temperature=1,
                    response_format={"type": "json_object"},
                    timeout=30,  # Add a timeout to prevent indefinite waiting
                )
                try:
                    response_json = json.loads(response.choices[0].message.content)
                    candidate_message = response_json.get("message", "")
                    code = response_json.get("code_and_notes", "")
                    finished = response_json.get("finished", False)
                    question = response_json.get("question", False)

                    if finished and not question and not code:
                        break
                except:
                    continue
            except Exception as e:
                print(f"Error in API call: {str(e)}, skipping this iteration")
                continue

        if not candidate_message and not code and mode != "empty":
            print("No message or code in response")
            continue

        if candidate_message:
            messages_candidate.append({"role": "assistant", "content": candidate_message})
            interview_data["transcript"].append(f"CANDIDATE MESSAGE: {candidate_message}")
        if code:
            interview_data["transcript"].append(f"CANDIDATE CODE AND NOTES: {code}")
            messages_candidate.append({"role": "assistant", "content": code})

        chat_display.append([candidate_message, None])

        send_time = time.time()

        # Fix: Iterate over all elements and keep the last one
        last_result = None
        for result in send_request(code, previous_code, messages_interviewer, chat_display, llm, tts=None, silent=True):
            last_result = result

        if last_result is not None:
            messages_interviewer, chat_display, previous_code, _ = last_result
        else:
            print("send_request did not return any results, skipping this iteration")
            continue

        response_times.append(time.time() - send_time)

        messages_candidate.append({"role": "user", "content": chat_display[-1][1]})

        message_split = messages_interviewer[-1]["content"].split("#NOTES#")
        interview_data["transcript"].append(f"INTERVIEWER MESSAGE: {message_split[0]}")

        if len(message_split) > 1:
            interview_data["transcript"].append(f"INTERVIEWER HIDDEN NOTE: {message_split[1]}")

        time.sleep(pause)  # to prevent exceeding rate limits

    # Fix: Iterate over all elements and keep the last one
    feedback = None
    for fb in llm.end_interview(problem_statement_text, messages_interviewer, interview_type):
        feedback = fb

    interview_data["feedback"] = feedback

    interview_data["average_response_time_seconds"] = round(sum(response_times) / len(response_times), 2) if response_times else 0

    current_time = time.strftime("%Y%m%d-%H%M%S")
    random_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    file_path = os.path.join("records", exp_name, f"{current_time}-{random_suffix}.json")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w") as file:
        json.dump(interview_data, file, indent=4)

    return file_path, interview_data
