import os
import gradio as gr

from api.audio import STTManager, TTSManager
from api.llm import LLMManager
from utils.config import Config
from resources.prompts import prompts
from ui.coding import get_problem_solving_ui
from ui.instructions import get_instructions_ui
from utils.params import default_audio_params


def initialize_services():
    """Initialize configuration, LLM, TTS, and STT services."""
    config = Config()
    llm = LLMManager(config, prompts)
    tts = TTSManager(config)
    stt = STTManager(config)
    default_audio_params["streaming"] = stt.streaming
    if os.getenv("SILENT", False):
        tts.read_last_message = lambda x: None
    return config, llm, tts, stt


def create_interface(llm, tts, stt, audio_params):
    """Create and configure the Gradio interface."""
    with gr.Blocks(title="AI Interviewer", theme=gr.themes.Default()) as demo:
        audio_output = gr.Audio(label="Play audio", autoplay=True, visible=os.environ.get("DEBUG", False), streaming=tts.streaming)
        get_problem_solving_ui(llm, tts, stt, audio_params, audio_output).render()
        get_instructions_ui(llm, tts, stt, audio_params).render()
    return demo


def main():
    """Main function to initialize services and launch the Gradio interface."""
    config, llm, tts, stt = initialize_services()
    demo = create_interface(llm, tts, stt, default_audio_params)
    demo.config["dependencies"][0]["show_progress"] = "hidden"
    demo.launch(show_api=False)


if __name__ == "__main__":
    main()
