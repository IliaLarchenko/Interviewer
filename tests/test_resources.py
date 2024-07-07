from resources.data import topic_lists, interview_types
from resources.prompts import prompts


def test_topics_completeness() -> None:
    """
    Test the completeness of topic lists.
    """

    assert len(topic_lists) == len(interview_types)
    for interview_type in interview_types:
        assert interview_type in topic_lists
        assert len(topic_lists[interview_type]) > 0


def test_prompts_completeness() -> None:
    """
    Test the completeness of prompts.
    """

    assert len(prompts) == len(interview_types) * 3
    for interview_type in interview_types:
        assert f"{interview_type}_problem_generation_prompt" in prompts
        assert f"{interview_type}_interviewer_prompt" in prompts
        assert f"{interview_type}_grading_feedback_prompt" in prompts
