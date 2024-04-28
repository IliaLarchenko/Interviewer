import os

import gradio as gr

from api.audio import STTManager, TTSManager
from api.llm import LLMManager
from config import config
from docs.instruction import instruction
from resources.prompts import prompts
from ui.coding import get_codding_ui
from ui.instructions import get_instructions_ui
from utils.params import default_audio_params

llm = LLMManager(config, prompts)
tts = TTSManager(config)
stt = STTManager(config)

default_audio_params["streaming"] = stt.streaming

# Interface

with gr.Blocks(title="AI Interviewer") as demo:
    audio_output = gr.Audio(label="Play audio", autoplay=True, visible=os.environ.get("DEBUG", False), streaming=tts.streaming)
    instructions_tab = get_instructions_ui(llm, tts, stt, default_audio_params)
    coding_tab = get_codding_ui(llm, tts, stt, default_audio_params, audio_output)

    instructions_tab.render()
    coding_tab.render()

demo.launch(show_api=False)
