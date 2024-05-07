import os

import gradio as gr

from api.audio import STTManager, TTSManager
from api.llm import LLMManager
from config import config
from resources.prompts import prompts
from ui.coding import get_problem_solving_ui
from ui.instructions import get_instructions_ui
from utils.params import default_audio_params

llm = LLMManager(config, prompts)
tts = TTSManager(config)
stt = STTManager(config)

default_audio_params["streaming"] = stt.streaming

if os.getenv("SILENT", False):
    tts.read_last_message = lambda x: None

# Interface

with gr.Blocks(title="AI Interviewer") as demo:
    audio_output = gr.Audio(label="Play audio", autoplay=True, visible=os.environ.get("DEBUG", False), streaming=tts.streaming)
    instructions_tab = get_instructions_ui(llm, tts, stt, default_audio_params)
    coding_tab = get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output, name="Coding", interview_type="coding")
    ml_design_tab = get_problem_solving_ui(
        llm, tts, stt, default_audio_params, audio_output, name="ML Design (Beta)", interview_type="ml_design"
    )
    ml_theory_tab = get_problem_solving_ui(
        llm, tts, stt, default_audio_params, audio_output, name="ML Theory (Beta)", interview_type="ml_theory"
    )
    system_design_tab = get_problem_solving_ui(
        llm, tts, stt, default_audio_params, audio_output, name="System Design (Beta)", interview_type="system_design"
    )
    math_design_tab = get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output, name="Math (Beta)", interview_type="math")
    sql_design_tab = get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output, name="SQL (Beta)", interview_type="sql")

    instructions_tab.render()
    coding_tab.render()
    ml_design_tab.render()
    system_design_tab.render()
    ml_theory_tab.render()
    math_design_tab.render()
    sql_design_tab.render()

demo.launch(show_api=False)
