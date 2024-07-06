import json
from typing import Dict, Any, List
from openai import OpenAI
from tests.testing_prompts import grader_prompt

BASE_URL = "https://api.openai.com/v1"
JSON_INDENT = 4


def format_interview_data(interview_data):
    return [
        f"Interview type: {interview_data['inputs']['interview_type']}",
        f"Interview difficulty: {interview_data['inputs']['difficulty']}",
        f"Interview topic: {interview_data['inputs']['topic']}",
    ]


def generate_interview_summary(interview_data: Dict[str, Any]) -> List[str]:
    """
    Generate a summary of the interview data.

    :param interview_data: Dictionary containing interview data.
    :return: List of summary strings.
    """
    summary = format_interview_data(interview_data)
    if interview_data["inputs"]["requirements"]:
        summary.append(f"Interview requirements: {interview_data['inputs']['requirements']}")
    summary.append(f"Problem statement proposed by interviewer: {interview_data['problem_statement']}")
    summary.append(f"\nTranscript of the whole interview below:")
    summary += interview_data["transcript"]
    summary.append(f"\nTHE MAIN PART OF THE INTERVIEW ENDED HERE.")
    summary.append(f"Feedback provided by interviewer: {interview_data['feedback']}")
    return summary


def grade(json_file_path: str, model: str = "gpt-4o", suffix: str = "") -> Dict[str, Any]:
    """
    Grade the interview data and provide feedback.

    :param json_file_path: Path to the JSON file containing interview data.
    :param model: Model to use for grading.
    :param suffix: Suffix to add to the feedback file name.
    :return: Feedback dictionary.
    """
    try:
        with open(json_file_path) as file:
            interview_data = json.load(file)
    except FileNotFoundError:
        return {"error": "File not found"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"}

    interview_summary_list = generate_interview_summary(interview_data)

    messages = [
        {"role": "system", "content": grader_prompt},
        {"role": "user", "content": f"Please evaluate the interviewer based on the following data: \n {'\n'.join(interview_summary_list)}"},
    ]

    feedback = call_openai_api(messages, model)

    populate_feedback_metadata(feedback, json_file_path, interview_data, model)
    calculate_overall_score(feedback)

    save_feedback(json_file_path, feedback, suffix)

    return feedback


def call_openai_api(messages, model):
    client = OpenAI(base_url=BASE_URL)
    response = client.chat.completions.create(model=model, messages=messages, temperature=0, response_format={"type": "json_object"})
    return json.loads(response.choices[0].message.content)


def populate_feedback_metadata(feedback: Dict[str, Any], json_file_path: str, interview_data: Dict[str, Any], model: str) -> None:
    """
    Populate feedback metadata with interview details.

    :param feedback: Feedback dictionary to populate.
    :param json_file_path: Path to the JSON file containing interview data.
    :param interview_data: Dictionary containing interview data.
    :param model: Model used for grading.
    """
    feedback.update(
        {
            "file_name": json_file_path,
            "agent_llm": interview_data["interviewer_llm"],
            "candidate_llm": interview_data["candidate_llm"],
            "grader_model": model,
            "type": interview_data["inputs"]["interview_type"],
            "difficulty": interview_data["inputs"]["difficulty"],
            "topic": interview_data["inputs"]["topic"],
            "average_response_time_seconds": interview_data["average_response_time_seconds"],
            "number_of_messages": len(interview_data["transcript"]),
        }
    )


def calculate_overall_score(feedback: Dict[str, Any]) -> None:
    """
    Calculate the overall score from the feedback.

    :param feedback: Feedback dictionary containing scores.
    """
    scores = [
        feedback[key]
        for key in feedback
        if (key.startswith("interviewer_") or key.startswith("feedback_") or key.startswith("problem_")) and feedback[key] is not None
    ]
    feedback["overall_score"] = sum(scores) / len(scores)


def save_feedback(json_file_path: str, feedback: Dict[str, Any], suffix: str) -> None:
    """
    Save the feedback to a JSON file.

    :param json_file_path: Path to the original JSON file.
    :param feedback: Feedback dictionary to save.
    :param suffix: Suffix to add to the feedback file name.
    """
    with open(json_file_path.replace(".json", f"_feedback_{suffix}.json"), "w") as file:
        json.dump(feedback, file, indent=JSON_INDENT)
