import os

import gradio as gr

from docs.instruction import instruction
from utils.ui import get_status_color


def get_instructions_ui(llm, tts, stt, default_audio_params):
    with gr.Tab("Instruction", render=False) as instruction_tab:
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown(instruction["introduction"])
            with gr.Column(scale=1):
                space = "&nbsp;" * 10

                tts_status = get_status_color(tts)
                gr.Markdown(f"TTS status: {tts_status}{space}{tts.config.tts.name}", elem_id="tts_status")

                stt_status = get_status_color(stt)
                gr.Markdown(f"STT status: {stt_status}{space}{stt.config.stt.name}", elem_id="stt_status")

                llm_status = get_status_color(llm)
                gr.Markdown(f"LLM status: {llm_status}{space}{llm.config.llm.name}", elem_id="llm_status")

        gr.Markdown(instruction["quick_start"])
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown(instruction["interface"])
            with gr.Column(scale=1):
                gr.Markdown("Bot interaction area will look like this. Use Record button to record your answer.")
                gr.Markdown("Click 'Send' to send you answer and get a reply.")
                chat_example = gr.Chatbot(
                    label="Chat", show_label=False, show_share_button=False, value=[["Candidate message", "Interviewer message"]]
                )
                send_btn_example = gr.Button("Send", interactive=False)
                audio_input_example = gr.Audio(interactive=True, **default_audio_params)
        gr.Markdown(instruction["models"])
        gr.Markdown(instruction["acknowledgements"])
        gr.Markdown(instruction["legal"])

    return instruction_tab
