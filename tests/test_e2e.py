from tests.candidate import complete_interview
from tests.grader import grade


def test_complete_interview():
    for _ in range(3):
        file_path, _ = complete_interview("coding", "test", model="gpt-3.5-turbo")
        feedback = grade(file_path, model="gpt-4-turbo")
        assert feedback["overall_score"] > 0.5
        if feedback["overall_score"] > 0.8:
            return
    assert False
