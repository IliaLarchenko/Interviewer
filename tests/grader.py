import json

from openai import OpenAI

from tests.testing_prompts import grader_prompt


def grade(json_file_path, model="gpt-4o", suffix=""):
    client = OpenAI(base_url="https://api.openai.com/v1")

    with open(json_file_path) as file:
        interview_data = json.load(file)

    interview_summary_list = []
    interview_summary_list.append(f"Interview type: {interview_data['inputs']['interview_type']}")
    interview_summary_list.append(f"Interview difficulty: {interview_data['inputs']['difficulty']}")
    interview_summary_list.append(f"Interview topic: {interview_data['inputs']['topic']}")
    if interview_data["inputs"]["requirements"] != "":
        interview_summary_list.append(f"Interview requirements: {interview_data['inputs']['requirements']}")
    interview_summary_list.append(f"Problem statement proposed by interviewer: {interview_data['problem_statement']}")
    interview_summary_list.append(f"\nTranscript of the whole interview below:")
    interview_summary_list += interview_data["transcript"]
    interview_summary_list.append(f"\nTHE MAIN PART OF THE INTERVIEW ENDED HERE.")
    interview_summary_list.append(f"Feedback provided by interviewer: {interview_data['feedback']}")

    messages = [
        {"role": "system", "content": grader_prompt},
        {"role": "user", "content": f"Please evaluate the interviewer based on the following data: \n {'\n'.join(interview_summary_list)}"},
    ]

    response = client.chat.completions.create(model=model, messages=messages, temperature=0, response_format={"type": "json_object"})
    feedback = json.loads(response.choices[0].message.content)

    feedback["file_name"] = json_file_path
    feedback["agent_llm"] = interview_data["interviewer_llm"]
    feedback["candidate_llm"] = interview_data["candidate_llm"]
    feedback["grader_model"] = model
    feedback["type"] = interview_data["inputs"]["interview_type"]
    feedback["difficulty"] = interview_data["inputs"]["difficulty"]
    feedback["topic"] = interview_data["inputs"]["topic"]
    feedback["average_response_time_seconds"] = interview_data["average_response_time_seconds"]
    feedback["number_of_messages"] = len(interview_data["transcript"])

    scores = [
        feedback[x]
        for x in feedback
        if (x.startswith("interviewer_") or x.startswith("feedback_") or x.startswith("problem_")) and feedback[x] is not None
    ]
    feedback["overall_score"] = sum(scores) / len(scores)

    # save results to json file in the same folder as the interview data
    with open(json_file_path.replace(".json", f"_feedback_{suffix}.json"), "w") as file:
        json.dump(feedback, file, indent=4)

    return feedback
