import os

import gradio as gr

from api.audio import STTManager, TTSManager
from api.llm import LLMManager
from utils.config import Config
from resources.prompts import prompts
from ui.coding import get_problem_solving_ui
from ui.instructions import get_instructions_ui
from utils.params import default_audio_params

config = Config()
llm = LLMManager(config, prompts)
tts = TTSManager(config)
stt = STTManager(config)

default_audio_params["streaming"] = stt.streaming

if os.getenv("SILENT", False):
    tts.read_last_message = lambda x: None

# Interface

with gr.Blocks(title="AI Interviewer") as demo:
    audio_output = gr.Audio(label="Play audio", autoplay=True, visible=os.environ.get("DEBUG", False), streaming=tts.streaming)
    tabs = [
        get_instructions_ui(llm, tts, stt, default_audio_params),
        get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output, name="Coding", interview_type="coding"),
        get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output, name="ML Design (Beta)", interview_type="ml_design"),
        get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output, name="ML Theory (Beta)", interview_type="ml_theory"),
        get_problem_solving_ui(
            llm, tts, stt, default_audio_params, audio_output, name="System Design (Beta)", interview_type="system_design"
        ),
        get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output, name="Math (Beta)", interview_type="math"),
        get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output, name="SQL (Beta)", interview_type="sql"),
    ]

    for tab in tabs:
        tab.render()

demo.launch(show_api=False)
