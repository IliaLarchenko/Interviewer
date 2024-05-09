import json

from openai import OpenAI

from tests.testing_prompts import grader_prompt


def grade(json_file_path, model="gpt-4-turbo"):
    client = OpenAI(url="https://api.openai.com/v1")

    with open(json_file_path) as file:
        interview_data = json.load(file)

    messages = [
        {"role": "system", "content": grader_prompt},
        {"role": "user", "content": f"Interview data: {interview_data}"},
        {"role": "user", "content": "Please evaluate the interview."},
    ]

    response = client.chat.completions.create(model=model, messages=messages, temperature=1, response_format={"type": "json_object"})
    feedback = json.loads(response.choices[0].message.content)

    feedback["file_name"] = json_file_path
    feedback["agent_llm"] = interview_data["interviewer_llm"]
    feedback["candidate_llm"] = interview_data["candidate_llm"]
    feedback["type"] = interview_data["inputs"]["interview_type"]
    feedback["difficulty"] = interview_data["inputs"]["difficulty"]
    feedback["topic"] = interview_data["inputs"]["topic"]
    feedback["average_response_time_seconds"] = interview_data["average_response_time_seconds"]
    feedback["number_of_messages"] = len(interview_data["transcript"])

    scores = [
        feedback[x]
        for x in feedback
        if x.startswith("interviewer_") or x.startswith("feedback_") or x.startswith("problem_") and feedback[x] is not None
    ]
    feedback["overall_score"] = sum(scores) / len(scores)

    # save results to json file in the same folder as the interview data
    with open(json_file_path.replace(".json", "_feedback.json"), "w") as file:
        json.dump(feedback, file, indent=4)

    return feedback
