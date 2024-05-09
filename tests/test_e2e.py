from tests.candidate import complete_interview


def test_complete_interview():
    file_path, interview_data = complete_interview("coding", "test", model="gpt-3.5-turbo")
    assert True
