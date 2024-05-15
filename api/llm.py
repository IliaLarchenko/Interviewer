import os
from openai import OpenAI
from utils.errors import APIError
from typing import List, Dict, Generator, Optional, Tuple


class PromptManager:
    def __init__(self, prompts: Dict[str, str]):
        self.prompts = prompts
        self.limit = os.getenv("DEMO_WORD_LIMIT")

    def add_limit(self, prompt: str) -> str:
        if self.limit:
            prompt += f" Keep your responses very short and simple, no more than {self.limit} words."
        return prompt

    def get_system_prompt(self, key: str) -> str:
        prompt = self.prompts[key]
        return self.add_limit(prompt)

    def get_problem_requirements_prompt(
        self, type: str, difficulty: Optional[str] = None, topic: Optional[str] = None, requirements: Optional[str] = None
    ) -> str:
        prompt = f"Create a {type} problem. Difficulty: {difficulty}. Topic: {topic} Additional requirements: {requirements}. "
        return self.add_limit(prompt)


class LLMManager:
    def __init__(self, config, prompts: Dict[str, str]):
        self.config = config
        self.client = OpenAI(base_url=config.llm.url, api_key=config.llm.key)
        self.prompt_manager = PromptManager(prompts)

        self.status = self.test_llm()
        self.streaming = self.test_llm_stream() if self.status else False

        if self.streaming:
            self.end_interview = self.end_interview_stream
            self.get_problem = self.get_problem_stream
            self.send_request = self.send_request_stream
        else:
            self.end_interview = self.end_interview_full
            self.get_problem = self.get_problem_full
            self.send_request = self.send_request_full

    def get_text(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = self.client.chat.completions.create(model=self.config.llm.name, messages=messages, temperature=1, max_tokens=2000)
            if not response.choices:
                raise APIError("LLM Get Text Error", details="No choices in response")
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise APIError(f"LLM Get Text Error: Unexpected error: {e}")

    def get_text_stream(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        try:
            response = self.client.chat.completions.create(
                model=self.config.llm.name, messages=messages, temperature=1, stream=True, max_tokens=2000
            )
        except Exception as e:
            raise APIError(f"LLM End Interview Error: Unexpected error: {e}")
        text = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                text += chunk.choices[0].delta.content
            yield text

    def test_llm(self) -> bool:
        try:
            self.get_text(
                [
                    {"role": "system", "content": "You just help me test the connection."},
                    {"role": "user", "content": "Hi!"},
                    {"role": "user", "content": "Ping!"},
                ]
            )
            return True
        except:
            return False

    def test_llm_stream(self) -> bool:
        try:
            for _ in self.get_text_stream(
                [
                    {"role": "system", "content": "You just help me test the connection."},
                    {"role": "user", "content": "Hi!"},
                    {"role": "user", "content": "Ping!"},
                ]
            ):
                pass
            return True
        except:
            return False

    def init_bot(self, problem: str, interview_type: str = "coding") -> List[Dict[str, str]]:
        system_prompt = self.prompt_manager.get_system_prompt(f"{interview_type}_interviewer_prompt")
        return [{"role": "system", "content": f"{system_prompt}\nThe candidate is solving the following problem:\n {problem}"}]

    def get_problem_prepare_messages(self, requirements: str, difficulty: str, topic: str, interview_type: str) -> List[Dict[str, str]]:
        system_prompt = self.prompt_manager.get_system_prompt(f"{interview_type}_problem_generation_prompt")
        full_prompt = self.prompt_manager.get_problem_requirements_prompt(interview_type, difficulty, topic, requirements)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt},
        ]

    def get_problem_full(self, requirements: str, difficulty: str, topic: str, interview_type: str = "coding") -> str:
        messages = self.get_problem_prepare_messages(requirements, difficulty, topic, interview_type)
        return self.get_text(messages)

    def get_problem_stream(
        self, requirements: str, difficulty: str, topic: str, interview_type: str = "coding"
    ) -> Generator[str, None, None]:
        messages = self.get_problem_prepare_messages(requirements, difficulty, topic, interview_type)
        yield from self.get_text_stream(messages)

    def update_chat_history(
        self, code: str, previous_code: str, chat_history: List[Dict[str, str]], chat_display: List[List[Optional[str]]]
    ) -> List[Dict[str, str]]:
        message = chat_display[-1][0]
        if code != previous_code:
            message += "\nMY NOTES AND CODE:\n" + code
        chat_history.append({"role": "user", "content": message})
        return chat_history

    def send_request_full(
        self, code: str, previous_code: str, chat_history: List[Dict[str, str]], chat_display: List[List[Optional[str]]]
    ) -> Tuple[List[Dict[str, str]], List[List[Optional[str]]], str]:
        chat_history = self.update_chat_history(code, previous_code, chat_history, chat_display)
        reply = self.get_text(chat_history)
        chat_display.append([None, reply.split("#NOTES#")[0].strip()])
        chat_history.append({"role": "assistant", "content": reply})
        return chat_history, chat_display, code

    def send_request_stream(
        self, code: str, previous_code: str, chat_history: List[Dict[str, str]], chat_display: List[List[Optional[str]]]
    ) -> Generator[Tuple[List[Dict[str, str]], List[List[Optional[str]]], str], None, None]:
        chat_history = self.update_chat_history(code, previous_code, chat_history, chat_display)
        chat_display.append([None, ""])
        chat_history.append({"role": "assistant", "content": ""})
        reply = self.get_text_stream(chat_history)
        for message in reply:
            chat_display[-1][1] = message.split("#NOTES#")[0].strip()
            chat_history[-1]["content"] = message
            yield chat_history, chat_display, code

    def end_interview_prepare_messages(
        self, problem_description: str, chat_history: List[Dict[str, str]], interview_type: str
    ) -> List[Dict[str, str]]:
        transcript = [f"{message['role'].capitalize()}: {message['content']}" for message in chat_history[1:]]
        system_prompt = self.prompt_manager.get_system_prompt(f"{interview_type}_grading_feedback_prompt")
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"The original problem to solve: {problem_description}"},
            {"role": "user", "content": "\n\n".join(transcript)},
            {"role": "user", "content": "Grade the interview based on the transcript provided and give feedback."},
        ]

    def end_interview_full(self, problem_description: str, chat_history: List[Dict[str, str]], interview_type: str = "coding") -> str:
        if len(chat_history) <= 2:
            return "No interview history available"
        messages = self.end_interview_prepare_messages(problem_description, chat_history, interview_type)
        return self.get_text(messages)

    def end_interview_stream(
        self, problem_description: str, chat_history: List[Dict[str, str]], interview_type: str = "coding"
    ) -> Generator[str, None, None]:
        if len(chat_history) <= 2:
            yield "No interview history available"
        messages = self.end_interview_prepare_messages(problem_description, chat_history, interview_type)
        yield from self.get_text_stream(messages)
