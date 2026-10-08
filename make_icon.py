"""Draw an original lowercase red e on black and generate multi-size Windows icons."""
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def chunk(tag, data):
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag+data) & 0xffffffff)

def glyph(x, y):
    outer = ((x-128)/76)**2 + ((y-128)/78)**2 <= 1
    inner = ((x-128)/49)**2 + ((y-128)/51)**2 < 1
    opening = x > 128 and 136 <= y <= 161
    crossbar = 114 <= y < 136
    return outer and ((not inner and not opening) or crossbar)

def render(size):
    samples = 4
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            coverage = sum(glyph((x+(sx+.5)/samples)*256/size,
                                 (y+(sy+.5)/samples)*256/size)
                           for sx in range(samples) for sy in range(samples))/(samples*samples)
            raw.extend((round(8+(229-8)*coverage), round(8+(9-8)*coverage),
                        round(10+(20-10)*coverage), 255))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')

def make_icons():
    sizes = [16,24,32,48,64,128,256]
    frames = [render(size) for size in sizes]
    entries, offset = [], 6+16*len(sizes)
    for size, frame in zip(sizes, frames):
        entries.append(struct.pack('<BBBBHHII',size%256,size%256,0,0,1,32,len(frame),offset))
        offset += len(frame)
    (ROOT / 'app.ico').write_bytes(struct.pack('<HHH',0,1,len(sizes))+b''.join(entries)+b''.join(frames))
    (ROOT / 'app-icon.png').write_bytes(frames[-1])
    (ROOT / 'app-icon.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
<rect width="256" height="256" fill="#08080a"/>
<defs><clipPath id="edge"><ellipse cx="128" cy="128" rx="76" ry="78"/></clipPath></defs>
<ellipse cx="128" cy="128" rx="76" ry="78" fill="#e50914"/>
<ellipse cx="128" cy="128" rx="49" ry="51" fill="#08080a"/>
<rect x="128" y="136" width="90" height="25" fill="#08080a"/>
<rect y="114" width="256" height="22" fill="#e50914" clip-path="url(#edge)"/>
</svg>''',encoding='utf-8')

if __name__ == '__main__':
    make_icons()
