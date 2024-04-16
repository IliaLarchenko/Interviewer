import gradio as gr

from llm import end_interview, get_problem, send_request

with gr.Blocks() as demo:
    gr.Markdown("Your coding interview practice AI assistant!")
    with gr.Tab("Coding"):
        chat_history = gr.State([])
        previous_code = gr.State("")
        with gr.Accordion("Settings") as init_acc:
            requirements = gr.Textbox(
                label="Requirements",
                placeholder=(
                    "Write any requirements here in a plain text: topic, difficulty, complexity, etc. "
                    "Or keep it blank to just get a random question."
                ),
            )
            # TODO: select language
            # TODO: select difficulty
            # TODO: select topic
            # TODO: select LLM model
            start_btn = gr.Button("Start")
        with gr.Accordion("Solution", open=True) as solution_acc:
            # TODO: auto open close
            with gr.Accordion("Problem description", open=True) as solution_acc:
                description = gr.Markdown()
            with gr.Row() as content:
                with gr.Column(scale=2):
                    code = gr.Code(label="Solution", language="python", lines=20)
                    message = gr.Textbox(label="Message", lines=1)
                    answer_btn = gr.Button("Send message")
                with gr.Column(scale=1):
                    chat = gr.Chatbot(label="Chat history")
                    end_btn = gr.Button("Finish the interview")
        with gr.Accordion("Feedback", open=True) as feedback_acc:
            feedback = gr.Markdown()

    start_btn.click(fn=get_problem, inputs=requirements, outputs=[description, chat_history], scroll_to_output=True)
    answer_btn.click(
        fn=send_request, inputs=[code, previous_code, message, chat_history, chat], outputs=[chat_history, chat, message, previous_code]
    )
    end_btn.click(fn=end_interview, inputs=chat_history, outputs=feedback)

demo.launch()
