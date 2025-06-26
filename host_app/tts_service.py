import base64
from google.oauth2 import service_account
from google.generativeai import GenerativeModel

# Configure Gemini TTS model
model = GenerativeModel(model_name="gemini-2.5-flash-preview")

def text_to_pcm(text: str) -> bytes:
    # Use Gemini 2.5 Flash Preview with audio response mode
    response = model.generate_content(
        text,
        generation_config={"response_mime_type": "audio/pcm"},
        stream=False,
    )

    # Get the Base64 audio blob
    part = response.parts[0]
    blob = part.inline_data
    return blob.data  # Already in PCM
