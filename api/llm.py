import os

from openai import OpenAI

from utils.errors import APIError


class LLMManager:
    def __init__(self, config, prompts):
        self.config = config
        self.client = OpenAI(base_url=config.llm.url, api_key=config.llm.key)
        self.prompts = prompts
        self.is_demo = os.getenv("IS_DEMO")
        self.demo_word_limit = os.getenv("DEMO_WORD_LIMIT")

        self.status = self.test_llm()
        if self.status:
            self.streaming = self.test_llm_stream()
        else:
            self.streaming = False

        if self.streaming:
            self.end_interview = self.end_interview_stream
        else:
            self.end_interview = self.end_interview_full

    def text_processor(self):
        def ans_full(response):
            return response

        def ans_stream(response):
            yield from response

        if self.streaming:
            return ans_full
        else:
            return ans_stream

    def get_text(self, messages):
        try:
            response = self.client.chat.completions.create(model=self.config.llm.name, messages=messages, temperature=1)
            if not response.choices:
                raise APIError("LLM Get Text Error", details="No choices in response")
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise APIError(f"LLM Get Text Error: Unexpected error: {e}")

    def get_text_stream(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=self.config.llm.name,
                messages=messages,
                temperature=1,
                stream=True,
            )
        except Exception as e:
            raise APIError(f"LLM End Interview Error: Unexpected error: {e}")
        text = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                text += chunk.choices[0].delta.content
            yield text

    test_messages = [
        {"role": "system", "content": "You just help me test the connection."},
        {"role": "user", "content": "Hi!"},
        {"role": "user", "content": "Ping!"},
    ]

    def test_llm(self):
        try:
            self.get_text(self.test_messages)
            return True
        except:
            return False

    def test_llm_stream(self):
        try:
            for _ in self.get_text_stream(self.test_messages):
                pass
            return True
        except:
            return False

    def init_bot(self, problem=""):
        system_prompt = self.prompts["coding_interviewer_prompt"]
        if self.is_demo:
            system_prompt += f" Keep your responses very short and simple, no more than {self.demo_word_limit} words."

        return [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"The candidate is solving the following problem: {problem}"},
        ]

    def get_problem(self, requirements, difficulty, topic):
        full_prompt = (
            f"Create a {difficulty} {topic} coding problem. "
            f"Additional requirements: {requirements}. "
            "The problem should be clearly stated, well-formatted, and solvable within 30 minutes. "
            "Ensure the problem varies each time to provide a wide range of challenges."
        )

        if self.is_demo:
            full_prompt += f" Keep your response very short and simple, no more than {self.demo_word_limit} words."

        question = self.get_text(
            [
                {"role": "system", "content": self.prompts["problem_generation_prompt"]},
                {"role": "user", "content": full_prompt},
            ]
        )

        chat_history = self.init_bot(question)
        return question, chat_history

    def send_request(self, code, previous_code, message, chat_history, chat_display):
        if code != previous_code:
            chat_history.append({"role": "user", "content": f"My latest code:\n{code}"})
        chat_history.append({"role": "user", "content": message})

        reply = self.get_text(chat_history)
        chat_history.append({"role": "assistant", "content": reply})

        if chat_display:
            chat_display[-1][1] = reply
        else:
            chat_display.append([message, reply])

        return chat_history, chat_display, "", code

    # TODO: implement both streaming and non-streaming versions
    def end_interview_prepare_messages(self, problem_description, chat_history):
        transcript = [f"{message['role'].capitalize()}: {message['content']}" for message in chat_history[1:]]

        system_prompt = self.prompts["grading_feedback_prompt"]
        if self.is_demo:
            system_prompt += f" Keep your response very short and simple, no more than {self.demo_word_limit} words."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"The original problem to solve: {problem_description}"},
            {"role": "user", "content": "\n\n".join(transcript)},
            {"role": "user", "content": "Grade the interview based on the transcript provided and give feedback."},
        ]

        return messages

    def end_interview_full(self, problem_description, chat_history):
        if len(chat_history) <= 2:
            return "No interview history available"
        else:
            messages = self.end_interview_prepare_messages(problem_description, chat_history)
            return self.get_text_stream(messages)

    def end_interview_stream(self, problem_description, chat_history):
        if len(chat_history) <= 2:
            yield "No interview history available"
        else:
            messages = self.end_interview_prepare_messages(problem_description, chat_history)
            yield from self.get_text_stream(messages)
