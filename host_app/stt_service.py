import io
import speech_recognition as sr
import openai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI()

recognizer = sr.Recognizer()

# async def transcribe_audio(audio_bytes: bytes):
#     if not audio_bytes:
#         raise ValueError("No audio bytes received.")
    
#     try:
#         with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
#             audio = recognizer.record(source)
#             return recognizer.recognize_google(audio)
#     except sr.UnknownValueError:
#         print("[STT] Could not understand audio.")
#         return None
#     except sr.RequestError as e:
#         raise RuntimeError(f"Speech recognition error: {e}")


# can be add like this if want to use multiple services and also update the frontend endpoint to select the service

# async def transcribe_audio(audio_bytes: bytes, service="google"):
async def transcribe_audio(service="google"):
    # if not audio_bytes:
    #     raise ValueError("No audio bytes received.")
    try:
        if service == "google":
            # with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            # with sr.AudioFile("sample.wav") as source:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                # audio = recognizer.record(source)
                audio = recognizer.listen(source, timeout=10)
                return recognizer.recognize_google(audio)
        elif service == "openai":
            # audio_file = openai.Audio.create(
            #     file=audio_bytes,
            #     model="whisper-1"
            # )
            # return audio_file.text
            # with open("temp_audio.wav", "wb") as f:
            #     f.write(audio_bytes)
            with open("temp_audio.wav", "rb") as audio_file:
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            return transcript.text
    except sr.UnknownValueError:
        print("[STT] Could not understand audio.")
        return None
    except Exception as e:
        raise RuntimeError(f"Speech recognition error: {e}") 
