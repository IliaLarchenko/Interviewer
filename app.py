import gradio as gr

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
            start_btn = gr.Button("Start")
        with gr.Accordion("Solution", open=True) as solution_acc:
            with gr.Accordion("Problem description", open=True) as solution_acc:
                description = gr.Markdown()
            with gr.Row() as content:
                with gr.Column(scale=2):
                    code = gr.Code(label="Solution", language="python", lines=20)
                    message = gr.Textbox(label="text", lines=1)
                    answer_btn = gr.Button("Send message")
                with gr.Column(scale=1):
                    chat = gr.Chatbot(label="Chat history")
                    end_btn = gr.Button("Finish the interview")
        with gr.Accordion("Feedback", open=True) as feedback_acc:
            feedback = gr.Markdown()

demo.launch()
