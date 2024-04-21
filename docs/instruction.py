# I will change it into proper format later

instruction = {
    "demo": """
<span style="color: red;">
    This is a demo version utilizing free API access with strict request limits. As a result, the experience may be slow, occasionally buggy, and not of the highest quality. If a model is unavailable, please wait for a minute before retrying. Persistent unavailability may indicate that the request limit has been reached, making the demo temporarily inaccessible.
    For a significantly better experience, please run the service locally and use your own OpenAI key or HuggingFace models.
</span>

                    """,
    "introduction": """
# Welcome to the AI Tech Interviewer Simulator!

Welcome to the AI Tech Interviewer Training tool! This tool is designed to help you practice for coding interviews by simulating the real interview experience. It's perfect for brushing up on your skills in a realistic setting, although it's not meant to replace actual interview preparations like studying algorithms or practicing coding problems.

## Key Features

- **Speech-First Interface**: You can talk to the tool just like you'd talk to a real interviewer. This makes practicing for your interviews more realistic.
- **Support for Various AI Models**: You can use different AI models with this tool, including:
  - **LLM (Large Language Model)**: Acts as the interviewer.
  - **Speech-to-Text and Text-to-Speech Models**: These help mimic a real conversation by converting spoken words to text and vice versa.
- **Model Flexibility**: The tool works with many different models, including ones from OpenAI and open-source models from Hugging Face.
- **Personal Project**: I created this tool as a fun way to experiment with AI models and to provide a helpful resource for interview practice.

## Compliance and Licensing

This tool is available under the Apache 2.0 license. Please make sure to follow all license agreements and terms of service for the models and APIs you use with this tool.

Check out the other sections for instructions on how to set up the tool, use the interview interface, configure models, and more.

""",
    "quick_start": """
# Running the AI Tech Interviewer Simulator

This guide provides detailed instructions for setting up and running the AI Tech Interviewer Simulator either using Docker (recommended for simplicity) or running it locally.

## Initial Setup

### Clone the Repository

First, clone the project repository to your local machine using the following command in your terminal:

```bash
git clone https://huggingface.co/spaces/IliaLarchenko/interviewer
cd interviewer
```

### Configure the Environment

Create a `.env` file from the provided example and edit it to include your OpenAI API key:

```bash
cp .env.openai.example .env
nano .env  # You can use any other text editor
```

Replace `OPENAI_API_KEY` in the `.env` file with your actual OpenAI API key.

## Option 1: Running with Docker

### Prerequisites

- Ensure **Docker** and **Docker Compose** are installed on your system. Download and install them from Docker's [official site](https://www.docker.com/get-started).

### Build and Run the Docker Container

Build and start the Docker container using the following commands:

```bash
docker-compose build
docker-compose up
```

### Access the Application

The application will be accessible at `http://localhost:7860`. Open this URL in your browser to start using the AI Tech Interviewer Simulator.

## Option 2: Running Locally

### Prerequisites

- Ensure you have **Python** installed on your system. Download and install it from [python.org](https://www.python.org).

### Set Up the Python Environment

Create a virtual environment to isolate the package dependencies:

```bash
python -m venv venv
source venv/bin/activate
```

### Install Dependencies

Install the required Python packages within the virtual environment:

```bash
pip install -r requirements.txt
```

### Running the Application

Start the server by executing:

```bash
python app.py
```

The application should now be accessible locally, typically at `http://localhost:7860`. Check your terminal output to confirm the URL.
""",
    "interface": """
# Interview Interface Overview

The AI Tech Interviewer Training tool currently supports different types of interviews, with only the coding interview available at this time. To begin, select the corresponding tab at the top of the interface.

## Interface Components

The interface is divided into four main sections, which you will navigate through sequentially:

### Setting
In this section, you can configure the interview parameters such as difficulty, topic, and any specific requirements in a free text form. Once you've set your preferences, click the **"Generate a problem"** button to start the interview. The AI will then prepare a coding problem for you.

### Problem Statement
After clicking **"Generate a problem"**, wait for less than 10 seconds, and the AI will present a coding problem in this section. Review the problem statement carefully to understand what is expected for your solution.

### Solution
This is where the main interaction occurs:
- **Code Area**: On the left side, you will find a space to write your solution. You can use any programming language, although syntax highlighting is only available for Python currently.
- **Communication Area**: On the right, this area includes:
  - **Chat History**: Displays the entire dialogue history, showing messages from both you and the AI interviewer.
  - **Audio Record Button**: Use this button to record your responses. Press to start recording, speak your thoughts, and press stop to send your audio. Your message will be transcribed and added to the chat, along with a snapshot of your code. For code-only messages, type your code and record a brief message like "Check out my code."

Engage with the AI as you would with a real interviewer. Provide concise responses and frequent updates rather than long monologues. Your interactions, including any commentary on your code, will be recorded and the AI's responses will be read aloud and displayed in the chat. Follow the AI's instructions and respond to any follow-up questions as they arise.

### Feedback
Once the interview is completed, or if you decide to end it early, click the **"Finish the interview"** button. Detailed feedback will be provided in this section, helping you understand your performance and areas for improvement.
                    """,
    "models": """
# Models Configuration

The AI Tech Interviewer Training tool utilizes three types of models: a Large Language Model (LLM) for simulating interviews, a Speech-to-Text (STT) model for audio processing, and a Text-to-Speech (TTS) model for auditory feedback. You can configure each model separately to tailor the experience based on your preferences and available resources.

## Flexible Model Integration

You can connect various models from different sources to the tool. Whether you are using models from OpenAI, Hugging Face, or even locally hosted models, the tool is designed to be compatible with a range of APIs. Here’s how you can configure each type:

### Large Language Model (LLM)

- **OpenAI Models**: You can use models like GPT-3.5-turbo or GPT-4 provided by OpenAI. Set up is straightforward with your OpenAI API key.
- **Hugging Face Models**: Models like Meta-Llama from Hugging Face can also be integrated. Make sure your API key has appropriate permissions.
- **Local Models**: If you have the capability, you can run models locally. Ensure they are compatible with the Hugging Face API for seamless integration.

### Speech-to-Text (STT)

- **OpenAI Whisper**: Available via OpenAI, this model supports multiple languages and dialects. It is also available in an open-source version on Hugging Face, giving you the flexibility to use it either through the OpenAI API or as a locally hosted version.
- **Other OS models**: Can be used too but can require a specific wrapper to align with API requirements.

### Text-to-Speech (TTS)

- **OpenAI Models**: The "tts-1" model from OpenAI is fast and produces human-like results, making it quite convenient for this use case.
- **Other OS models**: Can be used too but can require a specific wrapper to align with API requirements. In my experience, OS models sound more robotic than OpenAI models.

## Configuration via .env File

The tool uses a `.env` file for environment configuration. Here’s a breakdown of how this works:

- **API Keys**: Whether using OpenAI, Hugging Face, or other services, your API key must be specified in the `.env` file. This key should have the necessary permissions to access the models you intend to use.
- **Model URLs and Types**: Specify the API endpoint URLs for each model and their type (e.g., `OPENAI_API` for OpenAI models, `HF_API` for Hugging Face or local APIs).
- **Model Names**: Set the specific model name, such as `gpt-3.5-turbo` or `whisper-1`, to tell the application which model to interact with.

### Example Configuration

For OpenAI models:
```plaintext
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY
LLM_URL=https://api.openai.com/v1
LLM_TYPE=OPENAI_API
LLM_NAME=gpt-3.5-turbo
STT_URL=https://api.openai.com/v1
STT_TYPE=OPENAI_API
STT_NAME=whisper-1
TTS_URL=https://api.openai.com/v1
TTS_TYPE=OPENAI_API
TTS_NAME=tts-1
```

For a Hugging Face model integration:
```plaintext
HF_API_KEY=hf_YOUR_HUGGINGFACE_API_KEY
LLM_URL=https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-70B-Instruct/v1
LLM_TYPE=HF_API
LLM_NAME=Meta-Llama-3-70B-Instruct
STT_URL=https://api-inference.huggingface.co/models/openai/whisper-tiny.en
STT_TYPE=HF_API
STT_NAME=whisper-tiny.en
TTS_URL=https://api-inference.huggingface.co/models/facebook/mms-tts-eng
TTS_TYPE=HF_API
TTS_NAME=Facebook-mms-tts-eng
```

For local models:
```plaintext
HF_API_KEY=None
LLM_URL=http://192.168.1.1:8080/v1
LLM_TYPE=HF_API
LLM_NAME=Meta-Llama-3-8B-Instruct
STT_URL=http://127.0.0.1:5000/transcribe
STT_TYPE=HF_API
STT_NAME=whisper-base.en
TTS_URL=http://127.0.0.1:5001/read
TTS_TYPE=HF_API
TTS_NAME=my-tts-model
```

This section provides a comprehensive guide on how to configure and integrate different AI models into the tool, including handling the `.env` configuration file and adapting it to various sources.
 """,
    "acknowledgements": """
# Acknowledgements

This tool is powered by Gradio, enabling me to create an easy-to-use interface for AI-based interview practice. I thank Gradio for their fantastic platform.

## Thanks to the Model Providers

While this tool can integrate various AI models, I primarily utilize and sincerely appreciate technologies provided by the following organizations:

- **OpenAI**: For models like GPT-3.5, GPT-4, Whisper, and TTS-1. More details on their models and usage policies can be found at [OpenAI's website](https://www.openai.com).
- **Meta**: For the Llama models, particularly the Meta-Llama-3-70B-Instruct and Meta-Llama-3-8B-Instruct, crucial for advanced language processing. Visit [Meta AI](https://ai.facebook.com) for more information.
- **HuggingFace**: For a wide range of models and APIs that greatly enhance the flexibility of this tool. For specific details on usage, refer to [Hugging Face's documentation](https://huggingface.co).

Please ensure to review the specific documentation and follow the terms of service for each model and API you use, as this is crucial for responsible and compliant use of these technologies.

## Other Models

This tool is designed to be adaptable, allowing the integration of other models that comply with the APIs of the major providers listed. This enables the tool to be continually enhanced and tailored to specific needs.

I hope this tool assists you effectively in preparing for your interviews by leveraging these advanced technologies.

    """,
}
