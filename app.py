import gradio as gr

from llm import end_interview, get_problem, send_request
from options import languages_list, models, topics_list


def hide_settings():
    init_acc = gr.Accordion("Settings", open=False)
    start_btn = gr.Button("Generate a problem", interactive=False)
    solution_acc = gr.Accordion("Solution", open=True)
    return init_acc, start_btn, solution_acc


def hide_solution():
    solution_acc = gr.Accordion("Solution", open=False)
    end_btn = gr.Button("Finish the interview", interactive=False)
    problem_acc = gr.Accordion("Problem statement", open=False)
    return solution_acc, end_btn, problem_acc


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
                    code = gr.Code(label="Solution", language=language_select.value, lines=20)
                    message = gr.Textbox(label="Message", lines=1)
                    # TODO: add voice input and output
                with gr.Column(scale=1):
                    chat = gr.Chatbot(label="Chat history")
                    end_btn = gr.Button("Finish the interview")
        with gr.Accordion("Feedback", open=True) as feedback_acc:
            feedback = gr.Markdown()

    start_btn.click(
        fn=get_problem,
        inputs=[requirements, difficulty_select, topic_select, model_select],
        outputs=[description, chat_history],
        scroll_to_output=True,
    ).then(fn=hide_settings, inputs=None, outputs=[init_acc, start_btn, solution_acc])

    message.submit(
        fn=send_request,
        inputs=[code, previous_code, message, chat_history, chat, model_select],
        outputs=[chat_history, chat, message, previous_code],
    )

    end_btn.click(fn=end_interview, inputs=[chat_history, model_select], outputs=feedback).then(
        fn=hide_solution, inputs=None, outputs=[solution_acc, end_btn, problem_acc]
    )

demo.launch()
