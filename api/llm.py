import os
from openai import OpenAI
from utils.errors import APIError
from typing import List, Dict, Generator, Optional, Tuple


class PromptManager:
    def __init__(self, prompts: Dict[str, str]):
        self.prompts = prompts
        self.limit = os.getenv("DEMO_WORD_LIMIT")

    def add_limit(self, prompt: str) -> str:
        """
        Add word limit to the prompt if specified in the environment variables.
        """
        if self.limit:
            prompt += f" Keep your responses very short and simple, no more than {self.limit} words."
        return prompt

    def get_system_prompt(self, key: str) -> str:
        """
        Retrieve and limit a system prompt by its key.
        """
        prompt = self.prompts[key]
        return self.add_limit(prompt)

    def get_problem_requirements_prompt(
        self, type: str, difficulty: Optional[str] = None, topic: Optional[str] = None, requirements: Optional[str] = None
    ) -> str:
        """
        Create a problem requirements prompt with optional parameters.
        """
        prompt = f"Create a {type} problem. Difficulty: {difficulty}. Topic: {topic}. Additional requirements: {requirements}."
        return self.add_limit(prompt)


class LLMManager:
    def __init__(self, config, prompts: Dict[str, str]):
        self.config = config
        self.client = OpenAI(base_url=config.llm.url, api_key=config.llm.key)
        self.prompt_manager = PromptManager(prompts)

        self.status = self.test_llm(stream=False)
        self.streaming = self.test_llm(stream=True) if self.status else False

    def get_text(self, messages: List[Dict[str, str]], stream: Optional[bool] = None) -> Generator[str, None, None]:
        """
        Generate text from the LLM, optionally streaming the response.
        """
        if stream is None:
            stream = self.streaming
        try:
            if not stream:
                response = self.client.chat.completions.create(
                    model=self.config.llm.name, messages=messages, temperature=1, max_tokens=2000
                )
                yield response.choices[0].message.content.strip()
            else:
                response = self.client.chat.completions.create(
                    model=self.config.llm.name, messages=messages, temperature=1, stream=True, max_tokens=2000
                )
                text = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        text += chunk.choices[0].delta.content
                    yield text
        except Exception as e:
            raise APIError(f"LLM Get Text Error: Unexpected error: {e}")

    def test_llm(self, stream=False) -> bool:
        """
        Test the LLM connection with or without streaming.
        """
        try:
            list(
                self.get_text(
                    [
                        {"role": "system", "content": "You just help me test the connection."},
                        {"role": "user", "content": "Hi!"},
                        {"role": "user", "content": "Ping!"},
                    ],
                    stream=stream,
                )
            )
            return True
        except:
            return False

    def init_bot(self, problem: str, interview_type: str = "coding") -> List[Dict[str, str]]:
        """
        Initialize the bot with a system prompt and problem description.
        """
        system_prompt = self.prompt_manager.get_system_prompt(f"{interview_type}_interviewer_prompt")
        return [{"role": "system", "content": f"{system_prompt}\nThe candidate is solving the following problem:\n {problem}"}]

    def get_problem_prepare_messages(self, requirements: str, difficulty: str, topic: str, interview_type: str) -> List[Dict[str, str]]:
        """
        Prepare messages for generating a problem based on given requirements.
        """
        system_prompt = self.prompt_manager.get_system_prompt(f"{interview_type}_problem_generation_prompt")
        full_prompt = self.prompt_manager.get_problem_requirements_prompt(interview_type, difficulty, topic, requirements)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt},
        ]

    def get_problem(self, requirements: str, difficulty: str, topic: str, interview_type: str) -> Generator[str, None, None]:
        """
        Get a problem from the LLM based on the given requirements, difficulty, and topic.
        """
        messages = self.get_problem_prepare_messages(requirements, difficulty, topic, interview_type)
        yield from self.get_text(messages)

    def update_chat_history(
        self, code: str, previous_code: str, chat_history: List[Dict[str, str]], chat_display: List[List[Optional[str]]]
    ) -> List[Dict[str, str]]:
        """
        Update chat history with the latest user message and code.
        """
        message = chat_display[-1][0]
        if code != previous_code:
            message += "\nMY NOTES AND CODE:\n" + code
        chat_history.append({"role": "user", "content": message})
        return chat_history

    def send_request(
        self, code: str, previous_code: str, chat_history: List[Dict[str, str]], chat_display: List[List[Optional[str]]]
    ) -> Generator[Tuple[List[Dict[str, str]], List[List[Optional[str]]], str], None, None]:
        """
        Send a request to the LLM and update the chat display.
        """
        chat_history = self.update_chat_history(code, previous_code, chat_history, chat_display)
        chat_display.append([None, ""])
        chat_history.append({"role": "assistant", "content": ""})
        reply = self.get_text(chat_history)
        for message in reply:
            chat_display[-1][1] = message.split("#NOTES#")[0].strip()
            chat_history[-1]["content"] = message
            yield chat_history, chat_display, code

    def end_interview_prepare_messages(
        self, problem_description: str, chat_history: List[Dict[str, str]], interview_type: str
    ) -> List[Dict[str, str]]:
        """
        Prepare messages to end the interview and generate feedback.
        """
        transcript = [f"{message['role'].capitalize()}: {message['content']}" for message in chat_history[1:]]
        system_prompt = self.prompt_manager.get_system_prompt(f"{interview_type}_grading_feedback_prompt")
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"The original problem to solve: {problem_description}"},
            {"role": "user", "content": "\n\n".join(transcript)},
            {"role": "user", "content": "Grade the interview based on the transcript provided and give feedback."},
        ]

    def end_interview(
        self, problem_description: str, chat_history: List[Dict[str, str]], interview_type: str = "coding"
    ) -> Generator[str, None, None]:
        """
        End the interview and get feedback from the LLM.
        """
        if len(chat_history) <= 2:
            yield "No interview history available"
            return
        messages = self.end_interview_prepare_messages(problem_description, chat_history, interview_type)
        yield from self.get_text(messages)
