# Configuration!!!

# Account Configuration
Account_ID = 'PUT_ACCOUNT_ID_HERE'

# Theming
Favicon = 'favicon.ico'

# Image Hosting Configuration
Image_Hosting_Duration = 3600  # Time in seconds to host the image
Image_Cleanup_Interval = 300  # Interval for cleanup task (5 minutes)
Temporary_Image_Hosting_Location = 'tempfiles'  # Where to store files generated.

# System Configuration
Base_URL = 'https://api.cloudflare.com/client/v4/accounts'
Port=5050
MultiThreaded = True
Log_File = 'log.txt'
Debug = False

# Model Specification
# This is sent back whenever the /models endpoint is used. Do not change the formatting!
models = {
  "object": "list",
  "data": [
    {
        "id": "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
        "object": "model",
        "owned_by": "deepseek-ai-text-generation",
    },
    {
        "id": "@cf/deepseek-ai/deepseek-math-7b-instruct",
        "object": "model",
        "owned_by": "deepseek-ai-beta-text-generation",
    },
    {
        "id": "@cf/baai/bge-m3",
        "object": "model",
        "owned_by": "baai-text-embeddings",
    },
    {
        "id": "@cf/huggingface/distilbert-sst-2-int8",
        "object": "model",
        "owned_by": "huggingface-text-classification",
    },
    {
        "id": "@cf/meta/llama-guard-3-8b",
        "object": "model",
        "owned_by": "meta-text-generation",
    },
    {
        "id": "@cf/openai/whisper",
        "object": "model",
        "owned_by": "openai-speech-recognition",
    },
    {
        "id": "@cf/openai/whisper-tiny-en",
        "object": "model",
        "owned_by": "openai-beta-speech-recognition",
    },
    {
        "id": "@cf/meta/llama-2-7b-chat-fp16",
        "object": "model",
        "owned_by": "meta-text-generation",
    },
    {
        "id": "@cf/stabilityai/stable-diffusion-xl-base-1.0",
        "object": "model",
        "owned_by": "stabilityai-beta-image-generation",
    },
    {
        "id": "@cf/meta/llama-4-scout-17b-16e-instruct",
        "object": "model",
        "owned_by": "meta-text-generation",
    },
    {
        "id": "@cf/qwen/qwen1.5-14b-chat-awq",
        "object": "model",
        "owned_by": "qwen-text-generation",
    },
    {
        "id": "@cf/qwen/qwq-32b",
        "object": "model",
        "owned_by": "qwen-reasoning",
    }
  ],
  "object": "list"
}
