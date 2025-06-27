import base64
import requests
from google.generativeai import GenerativeModel  # Assuming you have a GenerativeModel class defined

model = GenerativeModel("models/tts-1")

def generate_audio_from_text(text: str) -> bytes:
    """
    Converts a text string to audio PCM bytes using Gemini 2.5 Flash Preview TTS.
    Returns raw audio bytes (PCM LINEAR16).
    """
    if not text:
        return b""

    try:
        # Use synchronous generation (single-shot, not streaming)
        response = model.generate_audio(text, stream=False)
        if hasattr(response, "audio") and response.audio:
            return response.audio
        else:
            raise RuntimeError("Gemini TTS response did not contain audio data.")
    except Exception as e:
        print(f"[TTS ERROR] Gemini TTS failed: {e}")
        raise
