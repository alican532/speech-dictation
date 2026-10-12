import struct
import threading
import time

from . import messages
from . import textproc
from . import usage
from . import vad

RATE = 16000
WIDTH = 2
MAX_PCM = 10 * 60 * RATE * WIDTH
MIN_VOICED = 0.25


class BatchSession:
    """Collects the recording and sends it in one request once it ends.

    It has the same surface as speech.LiveSession, so the app can use
    either one without knowing which service is behind it. A provider
    fills in transcribe().
    """

    missing_key = messages.REQUEST_FAILED

    def __init__(self, api_key, trim=True):
        self._key = (api_key or "").strip()
        self._trim = trim
        self._pcm = bytearray()
        self._closing = False
        self._recorded = 0.0
        # The dictation this belongs to, for the usage log.
        self.take = ""
        self.text = ""
        self.error = ""
        self.limit_hit = threading.Event()
        self.done = threading.Event()

    def fresh(self):
        return not self.done.is_set()

    def open(self):
        if not self._key:
            raise RuntimeError(self.missing_key)

    def push(self, pcm):
        if not pcm or self.done.is_set():
            return
        room = MAX_PCM - len(self._pcm)
        self._pcm.extend(pcm[:max(0, room)])
        if len(self._pcm) >= MAX_PCM:
            self.limit_hit.set()
            self.done.set()

    def finish(self):
        pcm = bytes(self._pcm)
        self._pcm = bytearray()
        try:
            if vad.voiced_seconds(pcm) < MIN_VOICED:
                raise RuntimeError(messages.NO_SPEECH)
            self._recorded = len(pcm) / (RATE * WIDTH)
            if self._trim:
                pcm = vad.trim(pcm)
            if not pcm:
                raise RuntimeError(messages.NO_SPEECH)
            text = textproc.clean(self.transcribe(pcm))
            if self._closing or not text:
                raise RuntimeError(messages.NO_SPEECH)
            self.text = text
            return text
        except RuntimeError as exc:
            self.error = str(exc)
            raise
        finally:
            self.done.set()

    def cancel(self):
        self._closing = True
        self._pcm = bytearray()
        self.done.set()

    def transcribe(self, pcm):
        raise NotImplementedError

    def _log(self, model, pcm, started, heard=None, **extra):
        """Logs one upload. heard is the text that came back, None when it failed."""
        if heard is None:
            status = "failed"
        elif self._closing:
            status = "cancelled"
        else:
            status = "done" if textproc.clean(heard) else "empty"
        usage.record("speech", model, seconds=len(pcm) / (RATE * WIDTH), recorded=self._recorded,
                     wait=time.monotonic() - started, status=status, billed=heard is not None,
                     take=self.take, **extra)


def wav(pcm):
    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * WIDTH, WIDTH, 16)
    header += b"data" + struct.pack("<I", len(pcm))
    return header + pcm
