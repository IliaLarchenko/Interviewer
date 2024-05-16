import gradio as gr
import numpy as np

from resources.data import fixed_messages, topic_lists
from utils.ui import add_candidate_message, add_interviewer_message


def get_problem_solving_ui(llm, tts, stt, default_audio_params, audio_output, name="Coding", interview_type="coding"):
    with gr.Tab(name, render=False, elem_id=f"{interview_type}_tab") as problem_tab:
        chat_history = gr.State([])
        previous_code = gr.State("")
        started_coding = gr.State(False)
        interview_type_var = gr.State(interview_type)
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
                            elem_id=f"{interview_type}_difficulty_select",
                        )
                    with gr.Row():
                        topics = topic_lists[interview_type].copy()
                        np.random.shuffle(topics)
                        gr.Markdown("Topic (can type custom value)")
                        topic_select = gr.Dropdown(
                            label="Select topic",
                            choices=topics,
                            value=topics[0],
                            container=False,
                            allow_custom_value=True,
                            elem_id=f"{interview_type}_topic_select",
                        )
                with gr.Column(scale=2):
                    requirements = gr.Textbox(
                        label="Requirements",
                        placeholder="Specify additional requirements",
                        lines=5,
                        elem_id=f"{interview_type}_requirements",
                    )
                    start_btn = gr.Button("Generate a problem", elem_id=f"{interview_type}_start_btn")

        with gr.Accordion("Problem statement", open=True) as problem_acc:
            description = gr.Markdown(elem_id=f"{interview_type}_problem_description")
        with gr.Accordion("Solution", open=False) as solution_acc:
            with gr.Row() as content:
                with gr.Column(scale=2):
                    if interview_type == "coding":
                        code = gr.Code(
                            label="Please write your code here. You can use any language, but only Python syntax highlighting is available.",
                            language="python",
                            lines=46,
                            elem_id=f"{interview_type}_code",
                        )
                    elif interview_type == "sql":
                        code = gr.Code(
                            label="Please write your query here.",
                            language="sql",
                            lines=46,
                            elem_id=f"{interview_type}_code",
                        )
                    else:
                        code = gr.Code(
                            label="Please write any notes for your solution here.",
                            language=None,
                            lines=46,
                            elem_id=f"{interview_type}_code",
                        )
                with gr.Column(scale=1):
                    end_btn = gr.Button("Finish the interview", interactive=False, variant="stop", elem_id=f"{interview_type}_end_btn")
                    chat = gr.Chatbot(label="Chat", show_label=False, show_share_button=False, elem_id=f"{interview_type}_chat")
                    message = gr.Textbox(
                        label="Message",
                        show_label=False,
                        lines=3,
                        max_lines=3,
                        interactive=True,
                        container=False,
                        elem_id=f"{interview_type}_message",
                    )
                    send_btn = gr.Button("Send", interactive=False, elem_id=f"{interview_type}_send_btn")
                    audio_input = gr.Audio(interactive=False, **default_audio_params, elem_id=f"{interview_type}_audio_input")

                    audio_buffer = gr.State(np.array([], dtype=np.int16))
                    transcript = gr.State({"words": [], "not_confirmed": 0, "last_cutoff": 0, "text": ""})

        with gr.Accordion("Feedback", open=True) as feedback_acc:
            feedback = gr.Markdown(elem_id=f"{interview_type}_feedback")

        # Start button click action chain
        start_btn.click(fn=add_interviewer_message(fixed_messages["start"]), inputs=[chat], outputs=[chat]).success(
            fn=lambda: True, outputs=[started_coding]
        ).success(fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]).success(
            fn=lambda: (gr.update(open=False), gr.update(interactive=False)), outputs=[init_acc, start_btn]
        ).success(
            fn=llm.get_problem,
            inputs=[requirements, difficulty_select, topic_select, interview_type_var],
            outputs=[description],
            scroll_to_output=True,
        ).success(
            fn=llm.init_bot, inputs=[description, interview_type_var], outputs=[chat_history]
        ).success(
            fn=lambda: (gr.update(open=True), gr.update(interactive=True), gr.update(interactive=True), gr.update(interactive=True)),
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
            fn=llm.end_interview, inputs=[description, chat_history, interview_type_var], outputs=[feedback]
        )

        send_btn.click(fn=add_candidate_message, inputs=[message, chat], outputs=[chat]).success(
            fn=lambda: None, outputs=[message]
        ).success(
            fn=llm.send_request,
            inputs=[code, previous_code, chat_history, chat],
            outputs=[chat_history, chat, previous_code],
        ).success(
            fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]
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
            audio_input.stop_recording(fn=lambda: gr.update(interactive=True), outputs=[send_btn])
        else:
            audio_input.stop_recording(fn=stt.speech_to_text_full, inputs=[audio_input], outputs=[message]).success(
                fn=lambda: gr.update(interactive=True), outputs=[send_btn]
            ).success(fn=lambda: None, outputs=[audio_input])

        # TODO: add proper messages and clean up when changing the interview type
        # problem_tab.select(fn=add_interviewer_message(fixed_messages["intro"]), inputs=[chat, started_coding], outputs=[chat]).success(
        #     fn=tts.read_last_message, inputs=[chat], outputs=[audio_output]
        # )

    return problem_tab
