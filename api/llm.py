import os

from openai import OpenAI


class LLMManager:
    def __init__(self, config, prompts):
        self.config = config
        self.client = OpenAI(base_url=config.llm.url, api_key=config.llm.key)
        self.prompts = prompts

    def test_connection(self):
        response = self.client.chat.completions.create(
            model=self.config.llm.name,
            messages=[
                {"role": "system", "content": "You just help me test the connection."},
                {"role": "user", "content": "Hi!"},
                {"role": "user", "content": "Ping!"},
            ],
        )
        return response.choices[0].message.content.strip()

    def init_bot(self, problem=""):

        system_prompt = self.prompts["coding_interviewer_prompt"]
        if os.getenv("IS_DEMO"):
            system_prompt += " Keep your responses very short and simple, no more than 100 words."

        chat_history = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"The candidate is solving the following problem: {problem}"},
        ]
        return chat_history

    def get_problem(self, requirements, difficulty, topic):
        full_prompt = (
            f"Create a {difficulty} {topic} coding problem. "
            f"Additional requirements: {requirements}. "
            "The problem should be clearly stated, well-formatted, and solvable within 30 minutes. "
            "Ensure the problem varies each time to provide a wide range of challenges."
        )

        if os.getenv("IS_DEMO"):
            full_prompt += " Keep your response very short and simple, no more than 200 words."

        response = self.client.chat.completions.create(
            model=self.config.llm.name,
            messages=[
                {"role": "system", "content": self.prompts["problem_generation_prompt"]},
                {"role": "user", "content": full_prompt},
            ],
            temperature=1.0,
        )
        question = response.choices[0].message.content.strip()
        chat_history = self.init_bot(question)
        return question, chat_history

    def send_request(self, code, previous_code, message, chat_history, chat_display):
        # Update chat history if code has changed
        if code != previous_code:
            chat_history.append({"role": "user", "content": f"My latest code:\n{code}"})
        chat_history.append({"role": "user", "content": message})

        # Process the updated chat history with the language model
        response = self.client.chat.completions.create(model=self.config.llm.name, messages=chat_history)
        reply = response.choices[0].message.content.strip()
        chat_history.append({"role": "assistant", "content": reply})

        # Update chat display with the new reply
        if chat_display:
            chat_display[-1][1] = reply
        else:
            chat_display.append([message, reply])

        # Return updated chat history, chat display, an empty string placeholder, and the unchanged code
        return chat_history, chat_display, "", code

    def end_interview(self, problem_description, chat_history):
        if not chat_history or len(chat_history) <= 2:
            return "No interview content available to review."

        transcript = []
        for message in chat_history[1:]:
            role = message["role"]
            content = f"{role.capitalize()}: {message['content']}"
            transcript.append(content)

        system_prompt = self.prompts["grading_feedback_prompt"]
        if os.getenv("IS_DEMO"):
            system_prompt += " Keep your response very short and simple, no more than 200 words."

        response = self.client.chat.completions.create(
            model=self.config.llm.name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"The original problem to solve: {problem_description}"},
                {"role": "user", "content": "\n\n".join(transcript)},
                {"role": "user", "content": "Grade the interview based on the transcript provided and give feedback."},
            ],
            temperature=0.5,
        )
        feedback = response.choices[0].message.content.strip()
        return feedback
