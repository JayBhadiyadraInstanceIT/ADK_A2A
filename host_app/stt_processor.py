import io
import wave
import speech_recognition as sr

def process_audio_to_text(pcm_bytes: bytes, sample_rate: int = 16000) -> str:
    """
    Converts raw PCM bytes (16-bit, mono) into text using SpeechRecognition.
    This function creates an in-memory WAV file from the PCM data.
    """
    with io.BytesIO() as wav_io:
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)      # mono
            wf.setsampwidth(2)      # 16-bit (2 bytes)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        wav_io.seek(0)
        audio_source = sr.AudioFile(wav_io)
        recognizer = sr.Recognizer()
        with audio_source as source:
            audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            text = ""
        except sr.RequestError as e:
            text = f"[STT Error: {e}]"
    return text
