# player.py
import pyaudio

class PCMPlayer:
    # def __init__(self, rate=24000, channels=1, format=pyaudio.paFloat32, chunk=1024):
    def __init__(self, rate=24000, channels=1, format=pyaudio.paInt16, chunk=1024):
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(format=format, channels=channels,
                                   rate=rate, output=True,
                                   frames_per_buffer=chunk)
        self.stream.start_stream()
    def write(self, data: bytes):
        self.stream.write(data)
    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
