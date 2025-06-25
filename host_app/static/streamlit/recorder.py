# recorder.py
import pyaudio

class PCMRecorder:
    def __init__(self, rate=16000, chunk=1024):
        self.rate = rate
        self.chunk = chunk
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(format=pyaudio.paInt16,
                                   channels=1,
                                   rate=self.rate,
                                   input=True,
                                   frames_per_buffer=self.chunk)
    def read(self):
        return self.stream.read(self.chunk, exception_on_overflow=False)
    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
