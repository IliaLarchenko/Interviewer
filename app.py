import gradio as gr

from llm import end_interview, get_problem, read_last_message, send_request, transcribe_audio
from options import languages_list, models, topics_list


def hide_settings():
    init_acc = gr.Accordion("Settings", open=False)
    start_btn = gr.Button("Generate a problem", interactive=False)
    solution_acc = gr.Accordion("Solution", open=True)
    end_btn = gr.Button("Finish the interview", interactive=True)
    send_btn = gr.Button("Send", interactive=True)
    audio_input = gr.Audio(
        label="Record audio",
        sources=["microphone"],
        type="filepath",
        waveform_options={"show_controls": False},
        interactive=True,
        editable=False,
    )
    chat = [
        (
            None,
            "Welcome to the interview! Please take a moment to read the problem statement. Then you can share you initial thoughts and ask any questions you may have. Good luck!",
        )
    ]
    return init_acc, start_btn, solution_acc, end_btn, send_btn, audio_input, chat


def hide_solution():
    solution_acc = gr.Accordion("Solution", open=False)
    end_btn = gr.Button("Finish the interview", interactive=False)
    problem_acc = gr.Accordion("Problem statement", open=False)
    send_btn = gr.Button("Send", interactive=False)
    audio_input = gr.Audio(
        label="Record audio",
        sources=["microphone"],
        type="filepath",
        waveform_options={"show_controls": False},
        interactive=False,
        editable=False,
    )
    return solution_acc, end_btn, problem_acc, send_btn, audio_input


def return_none():
    return None


with gr.Blocks() as demo:
    gr.Markdown("Your coding interview practice AI assistant!")
    # TODO: add instructions tab
    # TODO: add other types of interviews (e.g. system design, ML design, behavioral, etc.)

    with gr.Tab("Coding"):
        chat_history = gr.State([])
        previous_code = gr.State("")
        client = gr.State(None)
        with gr.Accordion("Settings") as init_acc:
            with gr.Row():
                with gr.Column():
                    gr.Markdown("Difficulty")
                    difficulty_select = gr.Dropdown(
                        label="Select difficulty", choices=["Easy", "Medium", "Hard"], value="Medium", container=False
                    )

                    gr.Markdown("Topic")
                    topic_select = gr.Dropdown(
                        label="Select topic", choices=topics_list, value="Arrays", container=False, allow_custom_value=True
                    )

                    gr.Markdown("Select LLM model to use")
                    model_select = gr.Dropdown(label="Select model", choices=models, value="gpt-3.5-turbo", container=False)
                with gr.Column():
                    requirements = gr.Textbox(
                        label="Requirements", placeholder="Specify requirements: topic, difficulty, language, etc.", lines=5
                    )
                    start_btn = gr.Button("Generate a problem")

            # TODO: select LLM model
        with gr.Accordion("Problem statement", open=True) as problem_acc:
            description = gr.Markdown()
        with gr.Accordion("Solution", open=False) as solution_acc:
            with gr.Row() as content:
                with gr.Column(scale=2):
                    language_select = gr.Dropdown(
                        label="Select language", choices=languages_list, value="python", container=False, interactive=True
                    )
                    code = gr.Code(label="Solution", language=language_select.value, lines=35)
                with gr.Column(scale=1):
                    end_btn = gr.Button("Finish the interview", interactive=False)
                    chat = gr.Chatbot(label="Chat history")
                    audio_input = gr.Audio(
                        label="Record audio",
                        sources=["microphone"],
                        type="filepath",
                        waveform_options={"show_controls": False},
                        interactive=False,
                        editable=False,
                    )
                    audio_output = gr.Audio(label="Play audio", autoplay=True, visible=False)
                    message = gr.Textbox(label="Message", lines=3)
                    send_btn = gr.Button("Send", interactive=False)

        with gr.Accordion("Feedback", open=True) as feedback_acc:
            feedback = gr.Markdown()

    start_btn.click(
        fn=get_problem,
        inputs=[requirements, difficulty_select, topic_select, model_select],
        outputs=[description, chat_history],
        scroll_to_output=True,
    ).then(fn=hide_settings, inputs=None, outputs=[init_acc, start_btn, solution_acc, end_btn, send_btn, audio_input, chat])

    send_btn.click(
        fn=send_request,
        inputs=[code, previous_code, message, chat_history, chat, model_select],
        outputs=[chat_history, chat, message, previous_code],
    )

    end_btn.click(fn=end_interview, inputs=[chat_history, model_select], outputs=feedback).then(
        fn=hide_solution, inputs=None, outputs=[solution_acc, end_btn, problem_acc, send_btn, audio_input]
    )

    audio_input.stop_recording(fn=transcribe_audio, inputs=[audio_input], outputs=[message]).then(
        fn=return_none, inputs=None, outputs=[audio_input]
    ).then(
        fn=send_request,
        inputs=[code, previous_code, message, chat_history, chat, model_select],
        outputs=[chat_history, chat, message, previous_code],
    )

    chat.change(fn=read_last_message, inputs=[chat], outputs=[audio_output])

    audio_output.stop(fn=return_none, inputs=None, outputs=[audio_output])

demo.launch()
