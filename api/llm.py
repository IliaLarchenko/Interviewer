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

    def test_connection(self):
        try:
            response = self.client.chat.completions.create(
                model=self.config.llm.name,
                messages=[
                    {"role": "system", "content": "You just help me test the connection."},
                    {"role": "user", "content": "Hi!"},
                    {"role": "user", "content": "Ping!"},
                ],
            )
            if not response.choices:
                raise APIError("LLM Test Connection Error", details="No choices in response")
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise APIError(f"LLM Test Connection Error: Unexpected error: {e}")

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

        try:
            response = self.client.chat.completions.create(
                model=self.config.llm.name,
                messages=[
                    {"role": "system", "content": self.prompts["problem_generation_prompt"]},
                    {"role": "user", "content": full_prompt},
                ],
                temperature=1.0,
            )
            if not response.choices:
                raise APIError("LLM Problem Generation Error", details="No choices in response")
            question = response.choices[0].message.content.strip()
        except Exception as e:
            raise APIError(f"LLM Problem Generation Error: Unexpected error: {e}")

        chat_history = self.init_bot(question)
        return question, chat_history

    def send_request(self, code, previous_code, message, chat_history, chat_display):
        if code != previous_code:
            chat_history.append({"role": "user", "content": f"My latest code:\n{code}"})
        chat_history.append({"role": "user", "content": message})

        try:
            response = self.client.chat.completions.create(model=self.config.llm.name, messages=chat_history)
            if not response.choices:
                raise APIError("LLM Send Request Error", details="No choices in response")
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            raise APIError(f"LLM Send Request Error: Unexpected error: {e}")

        chat_history.append({"role": "assistant", "content": reply})

        if chat_display:
            chat_display[-1][1] = reply
        else:
            chat_display.append([message, reply])

        return chat_history, chat_display, "", code

    def end_interview(self, problem_description, chat_history):

        if not chat_history or len(chat_history) <= 2:
            yield "No interview content available to review."

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

        if os.getenv("STREAMING", False):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.llm.name,
                    messages=messages,
                    temperature=0.5,
                    stream=True,
                )
            except Exception as e:
                raise APIError(f"LLM End Interview Error: Unexpected error: {e}")

            feedback = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    feedback += chunk.choices[0].delta.content
                yield feedback
        #     else:
        #         response = self.client.chat.completions.create(
        #             model=self.config.llm.name,
        #             messages=messages,
        #             temperature=0.5,
        #         )
        #         feedback = response.choices[0].message.content.strip()
        #         return feedback
