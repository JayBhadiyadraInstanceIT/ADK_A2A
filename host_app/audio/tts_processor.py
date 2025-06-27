import base64
from google.generativeai import GenerativeModel

class TTSProcessor:
    def __init__(self):
        self.model = GenerativeModel("models/tts-1")  # ✅ Correct TTS model

    async def stream_tts(self, text: str):
        """
        Streams TTS audio chunks as base64-encoded PCM.
        Yields: {"mime_type": "audio/pcm", "data": <base64_string>}
        """
        print(f"[TTS] Streaming TTS for: {text}")
        async for chunk in self.model.generate_audio_async(text, stream=True):
            if hasattr(chunk, "audio"):
                yield {
                    "mime_type": "audio/pcm",
                    "data": base64.b64encode(chunk.audio).decode("utf-8"),
                }
