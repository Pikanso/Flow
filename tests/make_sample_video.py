"""Turn the locally synthesized sample.wav into an MP4 test fixture."""
from pathlib import Path
from fractions import Fraction
import wave
import av
import numpy as np

root = Path(__file__).resolve().parents[1]
with wave.open(str(root / 'sample.wav')) as source:
    duration = source.getnframes() / source.getframerate()
output = av.open(str(root / 'sample.mp4'), 'w')
stream = output.add_stream('libx264', rate=24)
stream.width, stream.height, stream.pix_fmt = 640, 360, 'yuv420p'
audio_source = av.open(str(root / 'sample.wav'))
audio = output.add_stream('aac', rate=24000)
audio.layout = 'mono'
for i in range(int(duration*24)+1):
    pixels = np.zeros((360,640,3), dtype=np.uint8)
    pixels[:] = [35,62,48]
    pixels[170:190,40:40+int(560*i/(duration*24))] = [170,202,136]
    frame = av.VideoFrame.from_ndarray(pixels,format='rgb24')
    frame.pts = i
    for packet in stream.encode(frame): output.mux(packet)
for packet in stream.encode(): output.mux(packet)
resampler = av.AudioResampler(format='fltp',layout='mono',rate=24000)
for frame in audio_source.decode(audio=0):
    for converted in resampler.resample(frame):
        for packet in audio.encode(converted): output.mux(packet)
for converted in resampler.resample(None):
    for packet in audio.encode(converted): output.mux(packet)
for packet in audio.encode(): output.mux(packet)
audio_source.close()
output.close()
print('Created sample.mp4')
