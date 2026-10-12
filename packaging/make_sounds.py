"""Writes the start, stop and cancel chimes in assets/sounds.

Windows plays its own voice typing chimes. macOS and Linux have no such
files, so these short tones stand in for them. Run it again after changing
a tone; the WAV files are committed.
"""
import math
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "sounds")
RATE = 44100

# Each chime is a list of (frequency in Hz, start in s, length in s).
CHIMES = {
    "start": [(659.25, 0.00, 0.16), (987.77, 0.07, 0.22)],
    "stop": [(987.77, 0.00, 0.16), (659.25, 0.07, 0.22)],
    "cancel": [(523.25, 0.00, 0.20)],
}


def render(notes, volume=0.32):
    length = max(start + size for _, start, size in notes) + 0.02
    samples = [0.0] * int(length * RATE)
    for freq, start, size in notes:
        first = int(start * RATE)
        count = int(size * RATE)
        for i in range(count):
            t = i / RATE
            # Quick attack, soft exponential tail: a bell, not a beep.
            env = min(1.0, t / 0.006) * math.exp(-t * 14)
            tone = math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(4 * math.pi * freq * t)
            samples[first + i] += tone * env
    peak = max(abs(s) for s in samples) or 1.0
    return b"".join(struct.pack("<h", int(s / peak * volume * 32767)) for s in samples)


def write(path, pcm):
    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16)
    header += b"data" + struct.pack("<I", len(pcm))
    with open(path, "wb") as handle:
        handle.write(header + pcm)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, notes in CHIMES.items():
        path = os.path.join(OUT, name + ".wav")
        write(path, render(notes))
        print(path, os.path.getsize(path))


if __name__ == "__main__":
    main()
