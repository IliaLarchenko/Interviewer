# X_URL - the URL for the model endpoint, can be None if using OpenAI API
# X_TYPE - the type of the model, can be "OPENAI_API" or "HF_API"
# there should be an environment variable with the f"{}_KEY" name and the key as the value to authenticate the API
# X_NAME - the name of the model, used only for OpenAI API

LLM_URL = None
LLM_TYPE = "OPENAI_API"
LLM_NAME = "gpt-3.5-turbo"
# "gpt-3.5-turbo" - ~3 seconds delay with decent quality
# "gpt-4-turbo","gpt-4", etc. 10+ seconds delay but higher quality
# For HuggingFace models, the Messages API is used, it if compatible with Open AI API
# Don't forget to add "/v1" to the end of the URL for HuggingFace LLM models
# https://huggingface.co/docs/text-generation-inference/en/messages_api

STT_URL = "https://api-inference.huggingface.co/models/openai/whisper-tiny.en"
STT_TYPE = "HF_API"
STT_NAME = "whisper-1"
# "whisper-1" is the only OpenAI STT model available for OpenAI API
# The whisper family with more models is available on HuggingFace:
# https://huggingface.co/collections/openai/whisper-release-6501bba2cf999715fd953013
# you can also use any other compatible model from HuggingFace

TTS_URL = None
TTS_TYPE = "OPENAI_API"
TTS_NAME = "tts-1"
# OpenAI "tts-1" - very good quality and close to real-time response
# OpenAI "tts-1-hd" - slightly better quality with slightly longer response time (no obvious benefits in this case)
# I think OS models on HuggingFace have much more artificial voices, but you can try them out
