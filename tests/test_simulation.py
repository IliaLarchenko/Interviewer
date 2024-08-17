from concurrent.futures import ThreadPoolExecutor, as_completed
from tests.candidate import complete_interview
from tests.grader import grade
import random
import logging
from typing import List, Dict, Any, Tuple

# Constants
INTERVIEW_TYPES = ["ml_design", "math", "ml_theory", "system_design", "sql", "coding"]
EDGE_CASE_MODES = ["empty", "gibberish", "repeat"]
MIN_AVERAGE_SCORE = 0.7
MIN_INTERVIEW_SCORE = 0.2
MAX_WORKERS = 5


def complete_and_grade_interview(interview_type: str, mode: str = "normal") -> Dict[str, Any]:
    """
    Complete an interview and return the overall score and metadata.

    Args:
        interview_type (str): Type of the interview.
        mode (str): Mode of the interview ("normal", "empty", "gibberish", "repeat").

    Returns:
        Dict[str, Any]: Dictionary containing interview metadata and score.

    Raises:
        AssertionError: If the overall score is below the minimum score.
    """
    file_path, _ = complete_interview(interview_type, "test", model="gpt-4o-mini", mode=mode)
    feedback = grade(file_path, model="gpt-4o")
    score = feedback["overall_score"]

    assert (
        score > MIN_INTERVIEW_SCORE
    ), f"Score {score} is below minimum {MIN_INTERVIEW_SCORE} for {interview_type} interview in {mode} mode"

    return {"interview_type": interview_type, "mode": mode, "score": score}


def test_simulate_interview() -> None:
    """
    Test the complete interview process for various interview types, including edge cases.
    Runs interviews concurrently using a thread pool and checks the average score.
    """
    interview_configs: List[Tuple[str, str]] = [(it, "normal") for it in INTERVIEW_TYPES] + [
        (random.choice(INTERVIEW_TYPES), mode) for mode in EDGE_CASE_MODES
    ]

    valid_results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_config = {
            executor.submit(complete_and_grade_interview, interview_type, mode): (interview_type, mode)
            for interview_type, mode in interview_configs
        }

        for future in as_completed(future_to_config):
            interview_type, mode = future_to_config[future]
            try:
                result = future.result()
                valid_results.append(result)
                logging.info(f"Interview completed - Type: {result['interview_type']}, Mode: {result['mode']}, Score: {result['score']}")
            except Exception as e:
                logging.error(f"Interview failed - Type: {interview_type}, Mode: {mode}, Error: {str(e)}")

    # Calculate and log average score
    average_score = sum(result["score"] for result in valid_results) / len(valid_results)
    logging.info(f"Average score across all interviews: {average_score:.2f}")

    # Assert on the average score
    assert average_score > MIN_AVERAGE_SCORE, f"Average score {average_score:.2f} is below minimum {MIN_AVERAGE_SCORE}"

    # Log summary of results
    for interview_type in INTERVIEW_TYPES:
        type_scores = [r["score"] for r in valid_results if r["interview_type"] == interview_type]
        if type_scores:
            avg_type_score = sum(type_scores) / len(type_scores)
            logging.info(f"Average score for {interview_type}: {avg_type_score:.2f}")

    # Check that we have results for all interview types and edge cases
    tested_types = {r["interview_type"] for r in valid_results}
    tested_modes = {r["mode"] for r in valid_results}
    assert tested_types == set(INTERVIEW_TYPES), f"Not all interview types were tested. Missing: {set(INTERVIEW_TYPES) - tested_types}"
    assert tested_modes == set(
        EDGE_CASE_MODES + ["normal"]
    ), f"Not all modes were tested. Missing: {set(EDGE_CASE_MODES + ['normal']) - tested_modes}"
