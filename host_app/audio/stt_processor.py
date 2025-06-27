import io
import speech_recognition as sr
import time
import threading

class AudioBuffer:
    def __init__(self, max_duration=5.0, silence_timeout=1.2):
        self.max_duration = max_duration
        self.silence_timeout = silence_timeout
        self.audio_chunks = []
        self.last_audio_time = None
        self.lock = threading.Lock()

    def add_chunk(self, pcm_bytes):
        with self.lock:
            self.audio_chunks.append(pcm_bytes)
            self.last_audio_time = time.time()

    def is_ready(self):
        with self.lock:
            if not self.audio_chunks:
                return False
            duration = time.time() - self.last_audio_time
            return duration > self.silence_timeout

    def get_combined_audio(self):
        with self.lock:
            combined = b''.join(self.audio_chunks)
            self.audio_chunks = []
            return combined

class STTProcessor:
    def __init__(self):
        self.buffer = AudioBuffer()
        self.recognizer = sr.Recognizer()
        self.thread = threading.Thread(target=self._monitor_and_transcribe, daemon=True)
        self.transcript_callback = None
        self.running = False

    def start(self, transcript_callback):
        self.transcript_callback = transcript_callback
        self.running = True
        self.thread.start()

    def stop(self):
        self.running = False

    def add_pcm_chunk(self, pcm_bytes):
        self.buffer.add_chunk(pcm_bytes)

    def _monitor_and_transcribe(self):
        while self.running:
            if self.buffer.is_ready():
                combined = self.buffer.get_combined_audio()
                audio_data = sr.AudioData(combined, sample_rate=16000, sample_width=2)

                try:
                    text = self.recognizer.recognize_google(audio_data)
                    if self.transcript_callback:
                        self.transcript_callback(text)
                except sr.UnknownValueError:
                    print("❗ Could not understand audio")
                except sr.RequestError as e:
                    print(f"❗ STT error: {e}")
            time.sleep(0.1)
