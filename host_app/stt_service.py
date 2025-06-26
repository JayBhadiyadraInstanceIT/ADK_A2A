import io
import speech_recognition as sr
from fastapi import UploadFile

recognizer = sr.Recognizer()

async def transcribe_audio(file: UploadFile):
    audio_data = await file.read()
    with sr.AudioFile(io.BytesIO(audio_data)) as source:
        audio = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            raise RuntimeError(f"Speech recognition error: {e}")
