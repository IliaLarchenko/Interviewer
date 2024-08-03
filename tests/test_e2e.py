from tests.candidate import complete_interview
from tests.grader import grade
from concurrent.futures import ThreadPoolExecutor
import random
import logging
from typing import List


def complete_and_grade_interview(interview_type: str, mode: str = "normal", min_score=0.4) -> float:
    """
    Complete an interview and return the overall score.

    :param interview_type: Type of the interview.
    :param mode: Mode of the interview ("normal", "empty", "gibberish", "repeat").
    :return: Overall score of the interview.
    """
    file_path, _ = complete_interview(interview_type, "test", model="gpt-4o-mini", mode=mode)
    feedback = grade(file_path, model="gpt-4o")

    logging.info(f"Interview type: {interview_type}, mode: {mode}, score: {feedback['overall_score']}")
    assert feedback["overall_score"] > min_score
    return feedback["overall_score"]


def test_complete_interview() -> None:
    """
    Test the complete interview process for various interview types, including edge cases.
    """
    interview_types = ["ml_design", "math", "ml_theory", "system_design", "sql", "coding"]
    scores: List[float] = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        # Test normal interviews
        futures = [executor.submit(complete_and_grade_interview, it) for it in interview_types]

        # Test edge cases: empty, gibberish, repeat for one random interview type each
        futures.append(executor.submit(complete_and_grade_interview, random.choice(interview_types), mode="empty"))
        futures.append(executor.submit(complete_and_grade_interview, random.choice(interview_types), mode="gibberish"))
        futures.append(executor.submit(complete_and_grade_interview, random.choice(interview_types), mode="repeat"))

        for future in futures:
            score = future.result()
            scores.append(score)

    logging.info(f"Average score: {sum(scores) / len(scores)}")
    assert sum(scores) / len(scores) > 0.7
