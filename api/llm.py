import os

from openai import OpenAI

from utils.errors import APIError


class PromptManager:
    def __init__(self, prompts):
        self.prompts = prompts
        self.limit = os.getenv("DEMO_WORD_LIMIT")

    def add_limit(self, prompt):
        if self.limit:
            prompt += f" Keep your responses very short and simple, no more than {self.limit} words."
        return prompt

    def get_system_prompt(self, key):
        prompt = self.prompts[key]
        return self.add_limit(prompt)

    def get_problem_requirements_prompt(self, type, difficulty=None, topic=None, requirements=None):
        prompt = f"Create a {type} problem. Difficulty: {difficulty}. Topic: {topic} " f"Additional requirements: {requirements}. "
        return self.add_limit(prompt)


class LLMManager:
    def __init__(self, config, prompts):
        self.config = config
        self.client = OpenAI(base_url=config.llm.url, api_key=config.llm.key)
        self.prompt_manager = PromptManager(prompts)

        self.status = self.test_llm()
        if self.status:
            self.streaming = self.test_llm_stream()
        else:
            self.streaming = False

        if self.streaming:
            self.end_interview = self.end_interview_stream
            self.get_problem = self.get_problem_stream
            self.send_request = self.send_request_stream
        else:
            self.end_interview = self.end_interview_full
            self.get_problem = self.get_problem_full
            self.send_request = self.send_request_full

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
            response = self.client.chat.completions.create(model=self.config.llm.name, messages=messages, temperature=1, max_tokens=2000)
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
                max_tokens=2000,
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

    def init_bot(self, problem, interview_type="coding"):
        system_prompt = self.prompt_manager.get_system_prompt(f"{interview_type}_interviewer_prompt")

        return [
            {"role": "system", "content": system_prompt + f"\nThe candidate is solving the following problem:\n {problem}"},
        ]

    def get_problem_prepare_messages(self, requirements, difficulty, topic, interview_type):
        system_prompt = self.prompt_manager.get_system_prompt(f"{interview_type}_problem_generation_prompt")
        full_prompt = self.prompt_manager.get_problem_requirements_prompt(interview_type, difficulty, topic, requirements)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt},
        ]

        return messages

    def get_problem_full(self, requirements, difficulty, topic, interview_type="coding"):
        messages = self.get_problem_prepare_messages(requirements, difficulty, topic, interview_type)
        return self.get_text(messages)

    def get_problem_stream(self, requirements, difficulty, topic, interview_type="coding"):
        messages = self.get_problem_prepare_messages(requirements, difficulty, topic, interview_type)
        yield from self.get_text_stream(messages)

    def update_chat_history(self, code, previous_code, chat_history, chat_display):
        message = chat_display[-1][0]

        if code != previous_code:
            message += "\nMY NOTES AND CODE:\n"
            message += code

        chat_history.append({"role": "user", "content": message})

        return chat_history

    def send_request_full(self, code, previous_code, chat_history, chat_display):
        chat_history = self.update_chat_history(code, previous_code, chat_history, chat_display)

        reply = self.get_text(chat_history)
        chat_display.append([None, reply.split("#NOTES#")[0].strip()])
        chat_history.append({"role": "assistant", "content": reply})

        return chat_history, chat_display, code

    def send_request_stream(self, code, previous_code, chat_history, chat_display):
        chat_history = self.update_chat_history(code, previous_code, chat_history, chat_display)

        chat_display.append([None, ""])
        chat_history.append({"role": "assistant", "content": ""})

        reply = self.get_text_stream(chat_history)
        for message in reply:
            chat_display[-1][1] = message.split("#NOTES#")[0].strip()
            chat_history[-1]["content"] = message

            yield chat_history, chat_display, code

    def end_interview_prepare_messages(self, problem_description, chat_history, interview_type):
        transcript = [f"{message['role'].capitalize()}: {message['content']}" for message in chat_history[1:]]

        system_prompt = self.prompt_manager.get_system_prompt(f"{interview_type}_grading_feedback_prompt")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"The original problem to solve: {problem_description}"},
            {"role": "user", "content": "\n\n".join(transcript)},
            {"role": "user", "content": "Grade the interview based on the transcript provided and give feedback."},
        ]

        return messages

    def end_interview_full(self, problem_description, chat_history, interview_type="coding"):
        if len(chat_history) <= 2:
            return "No interview history available"
        else:
            messages = self.end_interview_prepare_messages(problem_description, chat_history, interview_type)
            return self.get_text(messages)

    def end_interview_stream(self, problem_description, chat_history, interview_type="coding"):
        if len(chat_history) <= 2:
            yield "No interview history available"
        else:
            messages = self.end_interview_prepare_messages(problem_description, chat_history, interview_type)
            yield from self.get_text_stream(messages)
