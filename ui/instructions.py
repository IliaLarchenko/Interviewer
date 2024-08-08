import gradio as gr

from utils.ui import get_status_color

INTRO = """
# Welcome to the AI Mock Interviewer!

You can try this service in the demo mode here: [AI Interviewer](https://huggingface.co/spaces/IliaLarchenko/interviewer).

But for the good experience you need to run it locally [Project repository](https://github.com/IliaLarchenko/Interviewer).

This tool is designed to help you practice various technical interviews by simulating real interview experiences. 
You can enhance your skills in coding, (machine learning) system design, and other topics. 
You can brush your interview skills in a realistic setting, although it’s not intended to replace thorough preparations like studying algorithms or practicing coding problems.

"""

INTERFACE = """
# Interface

AI interviewer supports multiple types of interviews, including Coding, System Design, Machine Learning System Design, Math, Stats, and Logic, SQL, and ML Theory. 
Each type is tailored to help you practice specific skills and knowledge areas. You can also chose the Custom interview type to practice any topic you want - the AI will generate a problem based on your input.
Here's how to navigate the interface:

### Setting
Configure the interview settings such as difficulty, topic, and any specific requirements. Start the interview by clicking the **"Generate a problem"** button.

### Problem Statement
The AI will present a problem after you initiate the session.

### Solution
This section is where the interaction happens:
- **Code/Solution Area**: On the left side, you will find a space to write your solution. For codding problem you can use any language, although syntax highlighting is only available for Python and SQL.
- **Communication Area**: On the right, this area includes:
  - **Chat History**: Displays the entire dialogue history, showing messages from both you and the AI interviewer. Your recognized speech will be shown here before being sent to the AI.
  - **Audio Record Button**: Use this button to record your responses. Press to start recording, speak your thoughts, and press stop to send your audio. Wait until everything you said is transcribed and then click stop. Your message will be sent to the chat, along with a snapshot of your code or any notes from solution text area."

Engage with the AI as you would with a real interviewer. Provide concise responses and frequent updates rather than long monologues. Your interactions, including any commentary on your code, will be recorded and the AI's responses will be read aloud and displayed in the chat. Follow the AI's instructions and respond to any follow-up questions as they arise.

Once the interview is completed, or if you decide to end it early, click the **"Finish the interview"** button.

### Feedback
Detailed feedback will be provided in this section after the interview is over, helping you understand your performance and areas for improvement.  
"""


def get_instructions_ui(llm, tts, stt, default_audio_params):
    with gr.Tab("Instruction", render=False) as instruction_tab:
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown(INTRO)
            with gr.Column(scale=1):
                space = "&nbsp;" * 10

                tts_status = get_status_color(tts)
                gr.Markdown(f"TTS status: {tts_status}{space}{tts.config.tts.name}", elem_id="tts_status")

                stt_status = get_status_color(stt)
                gr.Markdown(f"STT status: {stt_status}{space}{stt.config.stt.name}", elem_id="stt_status")

                llm_status = get_status_color(llm)
                gr.Markdown(f"LLM status: {llm_status}{space}{llm.config.llm.name}", elem_id="llm_status")

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown(INTERFACE)
            with gr.Column(scale=1):
                chat_example = gr.Chatbot(
                    label="Chat", show_label=False, show_share_button=False, value=[["Candidate message", "Interviewer message"]]
                )
                audio_input_example = gr.Audio(interactive=True, **default_audio_params)

    return instruction_tab
