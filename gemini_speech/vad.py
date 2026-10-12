import array
import time

RATE = 16000
WIDTH = 2
FRAME = RATE * WIDTH * 30 // 1000
# Room noise sits well under this. A soft voice on a laptop microphone lands
# around 600-1500, so the floor only rises above it in a loud room.
MIN_VOICE = 420


def frame_levels(pcm):
    samples = array.array("h")
    samples.frombytes(pcm[:len(pcm) - len(pcm) % 2])
    step = FRAME // WIDTH
    levels = []
    for start in range(0, len(samples) - step + 1, step):
        chunk = samples[start:start + step:2]
        total = 0
        for sample in chunk:
            total += sample * sample
        levels.append((total / len(chunk)) ** 0.5)
    return levels


def threshold(levels):
    if not levels:
        return MIN_VOICE
    ordered = sorted(levels)
    noise = ordered[len(ordered) // 5]
    return max(MIN_VOICE, noise * 2.8)


def voiced_seconds(pcm):
    levels = frame_levels(pcm)
    limit = threshold(levels)
    return sum(1 for value in levels if value >= limit) * 0.03


def trim(pcm, pad=0.25, keep_gap=0.35):
    """Drop the silence before, after and between phrases.

    Each voiced stretch keeps `pad` seconds on both sides so word edges
    survive, and every pause longer than that shrinks to `keep_gap` seconds.
    Whisper invents text on long silence, so this also guards the output.
    """
    levels = frame_levels(pcm)
    if not levels:
        return b""
    limit = threshold(levels)
    voiced = [value >= limit for value in levels]
    # A single loud frame is a click, not speech.
    for index in range(len(voiced)):
        if voiced[index]:
            left = index > 0 and voiced[index - 1]
            right = index + 1 < len(voiced) and voiced[index + 1]
            if not left and not right:
                voiced[index] = False
    pad_frames = int(pad / 0.03)
    keep = [False] * len(voiced)
    for index, flag in enumerate(voiced):
        if flag:
            for near in range(max(0, index - pad_frames), min(len(keep), index + pad_frames + 1)):
                keep[near] = True
    if not any(keep):
        return b""
    gap = b"\x00" * (int(keep_gap * RATE) * WIDTH)
    out = bytearray()
    index = 0
    while index < len(keep):
        if not keep[index]:
            index += 1
            continue
        end = index
        while end < len(keep) and keep[end]:
            end += 1
        if out:
            out.extend(gap)
        out.extend(pcm[index * FRAME:end * FRAME])
        index = end
    return bytes(out)


class Silence:
    """Follows the microphone level while recording.

    The floor adapts to the room for the first second, so a fan or a
    noisy street does not count as speech.
    """

    def __init__(self):
        self.reset()

    def reset(self, deaf=0.5):
        # The start chime plays through the speakers into the microphone.
        # It is not you speaking, so the first moment is not counted.
        self._deaf = deaf
        self._rest = b""
        self._noise = []
        self.started = time.monotonic()
        self.heard = False
        self.last_voice = self.started
        self.level = 0.0

    def feed(self, pcm):
        data = self._rest + pcm
        usable = len(data) - len(data) % FRAME
        self._rest = data[usable:]
        if not usable:
            return
        now = time.monotonic()
        deaf = now - self.started < self._deaf
        for value in frame_levels(data[:usable]):
            self.level = value
            if deaf:
                continue
            if len(self._noise) < 34:
                self._noise.append(value)
            limit = max(MIN_VOICE, threshold(self._noise) if len(self._noise) >= 10 else MIN_VOICE)
            if value >= limit:
                self.heard = True
                self.last_voice = now

    def quiet_for(self):
        return time.monotonic() - self.last_voice

    def elapsed(self):
        return time.monotonic() - self.started
