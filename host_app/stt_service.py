import io
import speech_recognition as sr

recognizer = sr.Recognizer()

async def transcribe_audio(audio_bytes: bytes):
    if not audio_bytes:
        raise ValueError("No audio bytes received.")
    
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)
            return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        print("[STT] Could not understand audio.")
        return None
    except sr.RequestError as e:
        raise RuntimeError(f"Speech recognition error: {e}")
