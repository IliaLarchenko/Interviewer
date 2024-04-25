import os

import gradio as gr

from api.audio import STTManager, TTSManager
from api.llm import LLMManager
from config import config
from docs.instruction import instruction
from resources.data import fixed_messages, topics_list
from resources.prompts import prompts
from utils.ui import add_candidate_message, add_interviewer_message

llm = LLMManager(config, prompts)
tts = TTSManager(config)
stt = STTManager(config)

default_audio_params = {
    "label": "Record answer",
    "sources": ["microphone"],
    "type": "numpy",
    "waveform_options": {"show_controls": False},
    "editable": False,
    "container": False,
    "show_share_button": False,
}


def hide_settings():
    init_acc = gr.Accordion("Settings", open=False)
    start_btn = gr.Button("Generate a problem", interactive=False)
    return init_acc, start_btn


def show_solution():
    solution_acc = gr.Accordion("Solution", open=True)
    end_btn = gr.Button("Finish the interview", interactive=True)
    audio_input = gr.Audio(interactive=True, **default_audio_params)
    return solution_acc, end_btn, audio_input


def hide_solution():
    solution_acc = gr.Accordion("Solution", open=False)
    end_btn = gr.Button("Finish the interview", interactive=False)
    problem_acc = gr.Accordion("Problem statement", open=False)
    audio_input = gr.Audio(interactive=False, **default_audio_params)
    return solution_acc, end_btn, problem_acc, audio_input


def get_status_color(obj):
    if obj.status:
        if obj.streaming:
            return "🟢"
        return "🟡"
    return "🔴"


# Interface

with gr.Blocks(title="AI Interviewer") as demo:
    if os.getenv("IS_DEMO"):
        gr.Markdown(instruction["demo"])

    started_coding = gr.State(False)
    audio_output = gr.Audio(label="Play audio", autoplay=True, visible=os.environ["DEBUG"], streaming=tts.streaming)
    with gr.Tab("Instruction") as instruction_tab:
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown(instruction["introduction"])
            with gr.Column(scale=1):
                space = "&nbsp;" * 10

                tts_status = get_status_color(tts)
                gr.Markdown(f"TTS status: {tts_status}{space}{config.tts.name}")

                try:
                    text_test = stt.speech_to_text(audio_test, False)
                    gr.Markdown(f"STT status: 🟢{space} {config.stt.name}")
                except:
                    gr.Markdown(f"STT status: 🔴{space} {config.stt.name}")

                llm_status = get_status_color(llm)
                gr.Markdown(f"LLM status: {llm_status}{space}{config.llm.name}")

        gr.Markdown(instruction["quick_start"])
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown(instruction["interface"])
            with gr.Column(scale=1):
                gr.Markdown("Bot interaction area will look like this. Use Record button to record your answer.")
                chat_example = gr.Chatbot(
                    label="Chat", show_label=False, show_share_button=False, value=[["Candidate message", "Interviewer message"]]
                )
                audio_input_example = gr.Audio(interactive=True, **default_audio_params)
        gr.Markdown(instruction["models"])
        gr.Markdown(instruction["acknowledgements"])

    with gr.Tab("Coding") as coding_tab:
        chat_history = gr.State([])
        previous_code = gr.State("")
        with gr.Accordion("Settings") as init_acc:
            with gr.Row():
                with gr.Column():
                    gr.Markdown("##### Problem settings")
                    with gr.Row():
                        gr.Markdown("Difficulty")
                        difficulty_select = gr.Dropdown(
                            label="Select difficulty",
                            choices=["Easy", "Medium", "Hard"],
                            value="Medium",
                            container=False,
                            allow_custom_value=True,
                        )
                    with gr.Row():
                        gr.Markdown("Topic (can type custom value)")
                        topic_select = gr.Dropdown(
                            label="Select topic", choices=topics_list, value="Arrays", container=False, allow_custom_value=True
                        )
                with gr.Column(scale=2):
                    requirements = gr.Textbox(label="Requirements", placeholder="Specify additional requirements", lines=5)
                    start_btn = gr.Button("Generate a problem")

        with gr.Accordion("Problem statement", open=True) as problem_acc:
            description = gr.Markdown()
        with gr.Accordion("Solution", open=False) as solution_acc:
            with gr.Row() as content:
                with gr.Column(scale=2):
                    code = gr.Code(
                        label="Please write your code here. You can use any language, but only Python syntax highlighting is available.",
                        language="python",
                        lines=35,
                    )
                with gr.Column(scale=1):
                    end_btn = gr.Button("Finish the interview", interactive=False)
                    chat = gr.Chatbot(label="Chat", show_label=False, show_share_button=False)
                    audio_input = gr.Audio(interactive=False, **default_audio_params)
                    # message = gr.Textbox(label="Message", lines=3, visible=False)

        with gr.Accordion("Feedback", open=True) as feedback_acc:
            feedback = gr.Markdown()

    # Events
    coding_tab.select(fn=add_interviewer_message(fixed_messages["intro"]), inputs=[chat, started_coding], outputs=[chat]).then(
        fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]
    )

    start_btn.click(fn=add_interviewer_message(fixed_messages["start"]), inputs=[chat], outputs=[chat]).then(
        fn=lambda: True, outputs=[started_coding]
    ).then(fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]).then(fn=hide_settings, outputs=[init_acc, start_btn]).then(
        fn=llm.get_problem,
        inputs=[requirements, difficulty_select, topic_select],
        outputs=[description],
        scroll_to_output=True,
    ).then(
        fn=llm.init_bot, inputs=[description], outputs=[chat_history]
    ).then(
        fn=show_solution, outputs=[solution_acc, end_btn, audio_input]
    )

    end_btn.click(
        fn=add_interviewer_message(fixed_messages["end"]),
        inputs=[chat],
        outputs=[chat],
    ).then(
        fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]
    ).then(fn=hide_solution, outputs=[solution_acc, end_btn, problem_acc, audio_input]).then(
        fn=llm.end_interview, inputs=[description, chat_history], outputs=[feedback]
    )

    audio_input.stop_recording(fn=stt.speech_to_text, inputs=[audio_input, chat], outputs=[chat]).then(
        fn=lambda: None, outputs=[audio_input]
    ).then(
        fn=llm.send_request,
        inputs=[code, previous_code, chat_history, chat],
        outputs=[chat_history, chat, previous_code],
    ).then(
        fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]
    )

demo.launch(show_api=False)
