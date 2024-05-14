from tests.candidate import complete_interview
from tests.grader import grade
from concurrent.futures import ThreadPoolExecutor


def complete_and_grade_interview(interview_type):
    file_path, _ = complete_interview(interview_type, "test", model="gpt-3.5-turbo")
    feedback = grade(file_path, model="gpt-4o")
    assert feedback["overall_score"] > 0.4
    return feedback["overall_score"]


def test_complete_interview():
    interview_types = ["ml_design", "math", "ml_theory", "system_design", "sql", "coding"]
    scores = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(complete_and_grade_interview, it) for it in interview_types]

        for future in futures:
            score = future.result()
            scores.append(score)

    assert sum(scores) / len(scores) > 0.6
