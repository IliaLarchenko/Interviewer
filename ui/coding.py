import gradio as gr
import numpy as np
import os

from itertools import chain

from resources.data import fixed_messages, topic_lists
from utils.ui import add_candidate_message, add_interviewer_message
from typing import List, Dict, Generator, Optional, Tuple
from functools import partial


def send_request(
    code: str, previous_code: str, chat_history: List[Dict[str, str]], chat_display: List[List[Optional[str]]], llm, tts
) -> Generator[Tuple[List[Dict[str, str]], List[List[Optional[str]]], str, bytes], None, None]:
    """
    Send a request to the LLM and update the chat display and translate it to speech.
    """
    # TODO: Find the way to simplify it and remove duplication in logic
    chat_history = llm.update_chat_history(code, previous_code, chat_history, chat_display)
    original_len = len(chat_display)
    chat_display.append([None, ""])
    chat_history.append({"role": "assistant", "content": ""})

    text_chunks = []
    reply = llm.get_text(chat_history)

    audio_generator = iter(())
    has_text_item = True
    has_audion_item = True
    audio_created = 0
    is_notes = False

    while has_text_item or has_audion_item:
        try:
            text_chunk = next(reply)
            text_chunks.append(text_chunk)
            has_text_item = True
        except StopIteration:
            has_text_item = False
            chat_history[-1]["content"] = "".join(text_chunks)

        try:
            audio_chunk = next(audio_generator)
            has_audion_item = True
        except StopIteration:
            audio_chunk = b""
            has_audion_item = False

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

        if len(chat_display) - original_len > audio_created + has_text_item:
            audio_generator = chain(audio_generator, tts.read_text(chat_display[original_len + audio_created][1]))
            audio_created += 1
            has_audion_item = True

        yield chat_history, chat_display, code, audio_chunk


def change_code_area(interview_type):
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


def get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output):
    send_request_partial = partial(send_request, llm=llm, tts=tts)

    with gr.Tab("Interview", render=False, elem_id=f"tab") as problem_tab:
        chat_history = gr.State([])
        previous_code = gr.State("")
        hi_markdown = gr.Markdown(
            "<h2 style='text-align: center;'> Hi! I'm here to guide you through a practice session for your technical interview. Choose the interview settings to begin.</h2>\n"
        )
        with gr.Row() as init_acc:
            with gr.Column(scale=3):
                interview_type_select = gr.Dropdown(
                    show_label=False,
                    info="Type of the interview.",
                    choices=["coding", "ml_design", "ml_theory", "system_design", "math", "sql"],
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
                    message = gr.Textbox(
                        label="Message",
                        show_label=False,
                        lines=3,
                        max_lines=3,
                        interactive=True,
                        container=False,
                        elem_id=f"message",
                    )
                    send_btn = gr.Button("Send", interactive=False, elem_id=f"send_btn")
                    audio_input = gr.Audio(interactive=False, **default_audio_params, elem_id=f"audio_input")

                    audio_buffer = gr.State(np.array([], dtype=np.int16))
                    transcript = gr.State({"words": [], "not_confirmed": 0, "last_cutoff": 0, "text": ""})

        with gr.Accordion("Feedback", open=True, visible=False) as feedback_acc:
            feedback = gr.Markdown(elem_id=f"feedback", line_breaks=True)

        # Start button click action chain
        start_btn.click(fn=add_interviewer_message(fixed_messages["start"]), inputs=[chat], outputs=[chat]).success(
            fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]
        ).success(
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
            fn=lambda: (gr.update(visible=True), gr.update(interactive=True), gr.update(interactive=True), gr.update(interactive=True)),
            outputs=[solution_acc, end_btn, audio_input, send_btn],
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
                gr.update(interactive=False),
            ),
            outputs=[solution_acc, end_btn, problem_acc, audio_input, send_btn],
        ).success(
            fn=lambda: (gr.update(visible=True)),
            outputs=[feedback_acc],
        ).success(
            fn=llm.end_interview, inputs=[description, chat_history, interview_type_select], outputs=[feedback]
        )

        send_btn.click(fn=add_candidate_message, inputs=[message, chat], outputs=[chat]).success(
            fn=lambda: None, outputs=[message]
        ).success(
            fn=send_request_partial,
            inputs=[code, previous_code, chat_history, chat],
            outputs=[chat_history, chat, previous_code, audio_output],
            # ).success(
            #     fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]
        ).success(
            fn=lambda: np.array([], dtype=np.int16), outputs=[audio_buffer]
        ).success(
            fn=lambda: {"words": [], "not_confirmed": 0, "last_cutoff": 0, "text": ""}, outputs=[transcript]
        )

        if stt.streaming:
            audio_input.stream(
                stt.process_audio_chunk,
                inputs=[audio_input, audio_buffer, transcript],
                outputs=[transcript, audio_buffer, message],
                show_progress="hidden",
            )
        else:
            audio_input.stop_recording(fn=stt.speech_to_text_full, inputs=[audio_input], outputs=[message]).success(
                fn=lambda: gr.update(interactive=True), outputs=[send_btn]
            ).success(fn=lambda: None, outputs=[audio_input])

        interview_type_select.change(
            fn=lambda x: gr.update(choices=topic_lists[x], value=np.random.choice(topic_lists[x])),
            inputs=[interview_type_select],
            outputs=[topic_select],
        ).success(fn=change_code_area, inputs=[interview_type_select], outputs=[code])

        terms_checkbox.change(fn=lambda x: gr.update(interactive=x), inputs=[terms_checkbox], outputs=[start_btn])
    return problem_tab
