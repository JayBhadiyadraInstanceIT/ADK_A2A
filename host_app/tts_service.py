import base64
from google.oauth2 import service_account
from google.generativeai import GenerativeModel

# Configure Gemini TTS model
# credentials = service_account.Credentials.from_service_account_file("your-service-account.json") # Replace with your service account file
# model = GenerativeModel(model_name="models/tts-1", credentials=credentials)
model = GenerativeModel(model_name="gemini-2.5-flash-preview-tts") # models/tts-1

def text_to_pcm(text: str) -> bytes:
    # Use Gemini 2.5 Flash Preview with audio response mode
    try:
        response = model.generate_content(
            text,
            generation_config={"response_mime_type": "audio/pcm"},
            stream=False,
        )

        # Get the Base64 audio blob
        part = response.parts[0]
        blob = part.inline_data
        return blob.data  # Already in PCM
    except Exception as e:
        raise RuntimeError(f"TTS generation failed: {e}")


# can be add like this if want to use multiple services and also update the frontend endpoint to select the service

# import elevenlabs
# def text_to_pcm(text: str, service="gemini") -> bytes:
#     if service == "gemini":
#         model = GenerativeModel(model_name="gemini-2.5-flash-preview-tts")
#         response = model.generate_content(
#             text,
#             generation_config={"response_mime_type": "audio/pcm"},
#             stream=False,
#         )
#         part = response.parts[0]
#         blob = part.inline_data
#         return blob.data
#     elif service == "elevenlabs":
#         audio = elevenlabs.generate(
#             text=text,
#             voice="your_voice_id"
#         )
#         return audio
