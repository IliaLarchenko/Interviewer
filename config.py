LLM_URL = f"https://api.openai.com/v1"
LLM_KEY_TYPE = "OPENAI_API_KEY"  # there should be an environment variable with this name
LLM_NAME = "gpt-3.5-turbo"
# "gpt-3.5-turbo" - ~3 seconds delay with decent quality
# "gpt-4-turbo","gpt-4", etc. 10+ seconds delay but higher quality

STT_URL = f"https://api.openai.com/v1"
STT_KEY_TYPE = "OPENAI_API_KEY"  # there should be an environment variable with this name
STT_NAME = "whisper-1"
# "whisper-1" - the only OpenAI STT model available


TTS_URL = f"https://api.openai.com/v1"
TTS_KEY_TYPE = "OPENAI_API_KEY"  # there should be an environment variable with this name
TTS_NAME = "tts-1"
# Recommended options
# "tts-1" - good quality and close to real-time response. Just use this one
# "tts-1-hd" - slightly better quality with slightly longer response time
