import gradio as gr
import numpy as np
import os
import time
from itertools import chain
from typing import List, Dict, Generator, Optional, Tuple, Any
from functools import partial

from resources.data import fixed_messages, topic_lists, interview_types
from utils.ui import add_candidate_message, add_interviewer_message
from api.llm import LLMManager
from api.audio import TTSManager, STTManager

DEMO_MESSAGE: str = """<span style="color: red;"> 
This service is running in demo mode with limited performance (e.g. slow voice recognition). For a better experience, run the service locally, refer to the Instruction tab for more details.
</span>"""


def send_request(
    code: str,
    previous_code: str,
    chat_history: List[Dict[str, str]],
    chat_display: List[List[Optional[str]]],
    llm: LLMManager,
    tts: Optional[TTSManager],
    silent: Optional[bool] = False,
) -> Generator[Tuple[List[Dict[str, str]], List[List[Optional[str]]], str, bytes], None, None]:
    """
    Send a request to the LLM and process the response.

    Args:
        code (str): Current code.
        previous_code (str): Previous code.
        chat_history (List[Dict[str, str]]): Current chat history.
        chat_display (List[List[Optional[str]]]): Current chat display.
        llm (LLMManager): LLM manager instance.
        tts (Optional[TTSManager]): TTS manager instance.
        silent (Optional[bool]): Whether to silence audio output. Defaults to False.

    Yields:
        Tuple[List[Dict[str, str]], List[List[Optional[str]]], str, bytes]: Updated chat history, chat display, code, and audio chunk.
    """

    # TODO: Find the way to simplify it and remove duplication in logic

    if silent is None:
        silent = os.getenv("SILENT", False)

    if chat_display[-1][0] is None and code == previous_code:
        yield chat_history, chat_display, code, b""
        return

    chat_history = llm.update_chat_history(code, previous_code, chat_history, chat_display)
    original_len = len(chat_display)
    chat_display.append([None, ""])

    text_chunks = []
    reply = llm.get_text(chat_history)

    chat_history.append({"role": "assistant", "content": ""})

    audio_generator = iter(())
    has_text_item = True
    has_audio_item = not silent
    audio_created = 0
    is_notes = False

    while has_text_item or has_audio_item:
        try:
            text_chunk = next(reply)
            text_chunks.append(text_chunk)
            has_text_item = True
        except StopIteration:
            has_text_item = False
            chat_history[-1]["content"] = "".join(text_chunks)

        if silent:
            audio_chunk = b""
        else:
            try:
                audio_chunk = next(audio_generator)
                has_audio_item = True
            except StopIteration:
                audio_chunk = b""
                has_audio_item = False

        if has_text_item and not is_notes:
            last_message = chat_display[-1][1]
            last_message += text_chunk

            split_notes = last_message.split("#NOTES#")
            if len(split_notes) > 1:
                is_notes = True
            last_message = split_notes[0]
            split_messages = last_message.split("\n\n")
            chat_display[-1][1] = split_messages[0]
            for m in split_messages[1:]:
                chat_display.append([None, m])

        if not silent:
            if len(chat_display) - original_len > audio_created + has_text_item:
                audio_generator = chain(audio_generator, tts.read_text(chat_display[original_len + audio_created][1]))
                audio_created += 1
                has_audio_item = True

        yield chat_history, chat_display, code, audio_chunk

    if chat_display and len(chat_display) > 1 and chat_display[-1][1] == "" and chat_display[-2][1]:
        chat_display.pop()
        yield chat_history, chat_display, code, b""


def change_code_area(interview_type: str) -> gr.update:
    """
    Update the code area based on the interview type.

    Args:
        interview_type (str): Type of interview.

    Returns:
        gr.update: Gradio update object for the code area.
    """
    if interview_type == "coding":
        return gr.update(
            label="Please write your code here. You can use any language, but only Python syntax highlighting is available.",
            language="python",
        )
    elif interview_type == "sql":
        return gr.update(
            label="Please write your query here.",
            language="sql",
        )
    else:
        return gr.update(
            label="Please write any notes for your solution here.",
            language=None,
        )


def get_problem_solving_ui(
    llm: LLMManager, tts: TTSManager, stt: STTManager, default_audio_params: Dict[str, Any], audio_output: gr.Audio
) -> gr.Tab:
    """
    Create the problem-solving UI for the interview application.

    Args:
        llm (LLMManager): LLM manager instance.
        tts (TTSManager): TTS manager instance.
        stt (STTManager): STT manager instance.
        default_audio_params (Dict[str, Any]): Default audio parameters.
        audio_output (gr.Audio): Gradio audio output component.

    Returns:
        gr.Tab: Gradio tab containing the problem-solving UI.
    """
    send_request_partial = partial(send_request, llm=llm, tts=tts)

    with gr.Tab("Interview", render=False, elem_id=f"tab") as problem_tab:
        if os.getenv("IS_DEMO"):
            gr.Markdown(DEMO_MESSAGE)
        chat_history = gr.State([])
        previous_code = gr.State("")
        start_time = gr.State(None)
        hi_markdown = gr.Markdown(
            "<h2 style='text-align: center;'> Hi! I'm here to guide you through a practice session for your technical interview. Choose the interview settings to begin.</h2>\n"
        )

        # UI components for interview settings
        with gr.Row() as init_acc:
            with gr.Column(scale=3):
                interview_type_select = gr.Dropdown(
                    show_label=False,
                    info="Type of the interview.",
                    choices=interview_types,
                    value="coding",
                    container=True,
                    allow_custom_value=False,
                    elem_id=f"interview_type_select",
                    scale=2,
                )
                difficulty_select = gr.Dropdown(
                    show_label=False,
                    info="Difficulty of the problem.",
                    choices=["Easy", "Medium", "Hard"],
                    value="Medium",
                    container=True,
                    allow_custom_value=True,
                    elem_id=f"difficulty_select",
                    scale=2,
                )
                topic_select = gr.Dropdown(
                    show_label=False,
                    info="Topic (you can type any value).",
                    choices=topic_lists[interview_type_select.value],
                    value=np.random.choice(topic_lists[interview_type_select.value]),
                    container=True,
                    allow_custom_value=True,
                    elem_id=f"topic_select",
                    scale=2,
                )
            with gr.Column(scale=4):
                requirements = gr.Textbox(
                    label="Requirements",
                    show_label=False,
                    placeholder="Specify additional requirements if any.",
                    container=False,
                    lines=5,
                    elem_id=f"requirements",
                )
                with gr.Row():
                    terms_checkbox = gr.Checkbox(
                        label="",
                        container=False,
                        value=not os.getenv("IS_DEMO", False),
                        interactive=True,
                        elem_id=f"terms_checkbox",
                        min_width=20,
                    )
                    with gr.Column(scale=100):
                        gr.Markdown(
                            "#### I agree to the [terms and conditions](https://github.com/IliaLarchenko/Interviewer?tab=readme-ov-file#important-legal-and-compliance-information)"
                        )
                start_btn = gr.Button("Generate a problem", elem_id=f"start_btn", interactive=not os.getenv("IS_DEMO", False))

        # Problem statement and solution components
        with gr.Accordion("Problem statement", open=True, visible=False) as problem_acc:
            description = gr.Markdown(elem_id=f"problem_description", line_breaks=True)
        with gr.Accordion("Solution", open=True, visible=False) as solution_acc:
            with gr.Row() as content:
                with gr.Column(scale=2):
                    code = gr.Code(
                        label="Please write your code here.",
                        language="python",
                        lines=46,
                        elem_id=f"code",
                    )
                with gr.Column(scale=1):
                    end_btn = gr.Button("Finish the interview", interactive=False, variant="stop", elem_id=f"end_btn")
                    chat = gr.Chatbot(label="Chat", show_label=False, show_share_button=False, elem_id=f"chat")

                    audio_input = gr.Audio(interactive=False, **default_audio_params, elem_id=f"audio_input")
                    audio_buffer = gr.State(np.array([], dtype=np.int16))
                    audio_to_transcribe = gr.State(np.array([], dtype=np.int16))

        with gr.Accordion("Feedback", open=True, visible=False) as feedback_acc:
            interview_time = gr.Markdown()
            feedback = gr.Markdown(elem_id=f"feedback", line_breaks=True)

        # Event handlers
        def start_timer():
            return time.time()

        def get_duration_string(start_time):
            if start_time is None:
                duration_str = ""
            else:
                duration = int(time.time() - start_time)
                minutes, seconds = divmod(duration, 60)
                duration_str = f"Interview duration: {minutes} minutes, {seconds} seconds"
            return duration_str

        start_btn.click(fn=start_timer, outputs=[start_time]).success(
            fn=add_interviewer_message(fixed_messages["start"]), inputs=[chat], outputs=[chat]
        ).success(fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]).success(
            fn=lambda: (
                gr.update(visible=False),
                gr.update(interactive=False),
                gr.update(interactive=False),
                gr.update(interactive=False),
                gr.update(visible=False),
            ),
            outputs=[init_acc, start_btn, terms_checkbox, interview_type_select, hi_markdown],
        ).success(
            fn=lambda: (gr.update(visible=True)),
            outputs=[problem_acc],
        ).success(
            fn=llm.get_problem,
            inputs=[requirements, difficulty_select, topic_select, interview_type_select],
            outputs=[description],
            scroll_to_output=True,
        ).success(
            fn=llm.init_bot, inputs=[description, interview_type_select], outputs=[chat_history]
        ).success(
            fn=lambda: (gr.update(visible=True), gr.update(interactive=True), gr.update(interactive=True)),
            outputs=[solution_acc, end_btn, audio_input],
        )

        end_btn.click(fn=lambda x: add_candidate_message("Let's stop here.", x), inputs=[chat], outputs=[chat]).success(
            fn=add_interviewer_message(fixed_messages["end"]),
            inputs=[chat],
            outputs=[chat],
        ).success(fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]).success(
            fn=lambda: (
                gr.update(open=False),
                gr.update(interactive=False),
                gr.update(open=False),
                gr.update(interactive=False),
            ),
            outputs=[solution_acc, end_btn, problem_acc, audio_input],
        ).success(
            fn=lambda: (gr.update(visible=True)),
            outputs=[feedback_acc],
        ).success(
            fn=llm.end_interview, inputs=[description, chat_history, interview_type_select], outputs=[feedback]
        ).success(
            fn=get_duration_string, inputs=[start_time], outputs=[interview_time]
        )

        hidden_text = gr.State("")
        is_transcribing = gr.State(False)

        audio_input.stream(
            stt.process_audio_chunk,
            inputs=[audio_input, audio_buffer],
            outputs=[audio_buffer, audio_to_transcribe],
        ).success(fn=lambda: True, outputs=[is_transcribing]).success(
            fn=stt.transcribe_audio, inputs=[audio_to_transcribe, hidden_text], outputs=[hidden_text]
        ).success(
            fn=stt.add_to_chat, inputs=[hidden_text, chat], outputs=[chat]
        ).success(
            fn=lambda: False, outputs=[is_transcribing]
        )

        # We need to wait until the last chunk of audio is transcribed before sending the request
        # I didn't find a native way of gradio to handle this, and used a workaround
        WAIT_TIME = 3
        TIME_STEP = 0.3
        STEPS = int(WAIT_TIME / TIME_STEP)

        stop_audio_recording = audio_input.stop_recording(fn=lambda: gr.update(visible=False), outputs=[audio_input])
        for _ in range(STEPS):
            stop_audio_recording = stop_audio_recording.success(fn=lambda x: time.sleep(TIME_STEP) if x else None, inputs=[is_transcribing])

        stop_audio_recording.success(
            fn=send_request_partial,
            inputs=[code, previous_code, chat_history, chat],
            outputs=[chat_history, chat, previous_code, audio_output],
            show_progress="full",
        ).then(fn=lambda: (np.array([], dtype=np.int16), "", False), outputs=[audio_buffer, hidden_text, is_transcribing]).then(
            fn=lambda: gr.update(visible=True), outputs=[audio_input]
        )

        interview_type_select.change(
            fn=lambda x: gr.update(choices=topic_lists[x], value=np.random.choice(topic_lists[x])),
            inputs=[interview_type_select],
            outputs=[topic_select],
        ).success(fn=change_code_area, inputs=[interview_type_select], outputs=[code])

        terms_checkbox.change(fn=lambda x: gr.update(interactive=x), inputs=[terms_checkbox], outputs=[start_btn])
    return problem_tab
