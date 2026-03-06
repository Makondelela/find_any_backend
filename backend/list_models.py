"""Check available Gemini models"""
from google import genai

client = genai.Client(api_key="AIzaSyB9yYOOqHHw_-NC9zM68FcgQQVSYJRXjj8")

print("Listing available models...\n")
for model in client.models.list():
    print(f"Model: {model.name}")
    if hasattr(model, 'supported_generation_methods'):
        print(f"  Methods: {model.supported_generation_methods}")
    print()
