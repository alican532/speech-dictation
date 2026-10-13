"""ElevenLabs Scribe: Scribe v2 after the recording ends, or Scribe v2
Realtime while you speak."""

import base64
import json
import queue
import re
import threading
import time

from . import messages
from . import net
from . import speech
from . import textproc
from . import usage
from .audio import level
from .batch import BatchSession

HOST = "api.elevenlabs.io"
URL = "https://%s/v1/speech-to-text" % HOST
LIVE_PATH = "/v1/speech-to-text/realtime"
BATCH_MODEL = "scribe_v2"
LIVE_MODEL = "scribe_v2_realtime"
RATE = 16000
WIDTH = 2
CHUNK = RATE * WIDTH // 4  # 250 ms
MAX_PCM = 10 * 60 * RATE * WIDTH
# The server commits by itself after about 36 s of audio. Committing a
# little earlier, in a pause between sentences, keeps them whole.
COMMIT_AFTER = 20 * RATE * WIDTH
QUIET = 400
PAUSE = RATE * WIDTH // 2
# More than 100 terms makes every request bill at least 20 s.
BATCH_TERMS = (100, 49)
LIVE_TERMS = (50, 20)
LIVE_ERRORS = {
    "auth_error": messages.ELEVENLABS_KEY_REJECTED,
    "quota_exceeded": messages.ELEVENLABS_QUOTA,
    "rate_limited": messages.ELEVENLABS_RATE_LIMIT,
    "commit_throttled": messages.ELEVENLABS_RATE_LIMIT,
    "session_time_limit_exceeded": messages.RECORDING_TOO_LONG,
}


def keyterms(vocabulary, limits):
    count, length = limits
    terms = []
    for word in textproc.words_of(vocabulary):
        word = re.sub(r"[<>{}\[\]\\]", "", word).strip()
        if word and len(word) <= length and len(word.split()) <= 5:
            terms.append(word)
    return terms[:count]


class ElevenLabsSession(BatchSession):
    """Sends the recording to Scribe v2 once it ends.

    edit is None, or ("correct" | "translate", instruction): ElevenLabs then
    runs the instruction on the transcript in the same request.
    """

    missing_key = messages.ELEVENLABS_KEY_MISSING

    def __init__(self, api_key, language="", trim=True, vocabulary="", no_verbatim=True, edit=None):
        super().__init__(api_key, trim)
        self._language = (language or "").strip()
        self._terms = keyterms(vocabulary, BATCH_TERMS)
        self._no_verbatim = no_verbatim
        self._edit = edit

    def transcribe(self, pcm):
        fields = [
            ("model_id", BATCH_MODEL),
            ("file_format", "pcm_s16le_16"),
            ("tag_audio_events", "false"),
            ("no_verbatim", "true" if self._no_verbatim else "false"),
        ]
        if self._language:
            fields.append(("language_code", self._language))
        if self._terms:
            fields.append(("keyterms", self._terms))
        if self._edit:
            fields.append(("transcript_edit", self._edit[1]))
        body, content_type = net.multipart(fields, "speech.pcm", "application/octet-stream", pcm)
        extra = {"keyterms": bool(self._terms), "edit": bool(self._edit)}
        started = time.monotonic()
        try:
            data = net.post("elevenlabs", URL, body, content_type, {"xi-api-key": self._key}, timeout=60)
        except RuntimeError:
            self._log(BATCH_MODEL, pcm, started, **extra)
            raise
        text = (data.get("text") or "").strip()
        self._log(BATCH_MODEL, pcm, started, text, **extra)
        return _edited(self._edit, text, _edit_text(data.get("edited_transcript")))


class ElevenLabsLive:
    """Streams the microphone to Scribe v2 Realtime while you speak."""

    def __init__(self, api_key, language="", vocabulary="", no_verbatim=True):
        self._key = (api_key or "").strip()
        self._language = (language or "").strip()
        self._terms = keyterms(vocabulary, LIVE_TERMS)
        self._no_verbatim = no_verbatim
        self._queue = queue.Queue()
        self._thread = None
        self._sock = None
        self._buf = bytearray()
        self._sent = 0
        self._since_commit = 0
        self._quiet = 0
        self._closing = False
        self._committed = []
        self._partial = ""
        self._stopped_at = 0.0
        self.take = ""
        self.text = ""
        self.error = ""
        self.limit_hit = threading.Event()
        self.done = threading.Event()

    def fresh(self):
        return not self.done.is_set() and not self.error

    def open(self):
        if not self._key:
            raise RuntimeError(messages.ELEVENLABS_KEY_MISSING)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def push(self, pcm):
        if pcm and not self.done.is_set():
            self._queue.put(pcm)

    def finish(self):
        self._stopped_at = time.monotonic()
        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=25)
        text = textproc.clean(self.text)
        if text and not self._closing:
            return text
        if self.error:
            raise RuntimeError(self.error)
        raise RuntimeError(messages.NO_SPEECH)

    def cancel(self):
        self._closing = True
        self._queue.put(None)
        self._close()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _query(self):
        query = {
            "model_id": LIVE_MODEL,
            "audio_format": "pcm_16000",
            "commit_strategy": "manual",
            "no_verbatim": "true" if self._no_verbatim else "false",
        }
        if self._language:
            query["language_code"] = self._language
        if self._terms:
            query["keyterms"] = self._terms
        return query

    def _run(self):
        try:
            try:
                self._sock = speech._connect(self._key, HOST, LIVE_PATH, self._query(), {"xi-api-key": self._key})
            except RuntimeError as exc:
                if " 401 " in str(exc) or " 403 " in str(exc):
                    raise RuntimeError(messages.ELEVENLABS_KEY_REJECTED) from None
                raise
            started = self._wait_for("session_started", 10)
            if not started and not self.error:
                raise RuntimeError(messages.ELEVENLABS_OFFLINE)
            pending = bytearray()
            ending = False
            while not self._closing and not self.error:
                self._drain(0)
                item = self._take(0.02)
                if item:
                    pending.extend(item)
                if item is None:
                    ending = True
                while len(pending) >= CHUNK or (ending and pending):
                    piece = bytes(pending[:CHUNK])
                    del pending[:CHUNK]
                    if self._sent + len(piece) > MAX_PCM:
                        self.limit_hit.set()
                        ending = True
                        pending.clear()
                        break
                    # A long take is committed in a pause, before the server cuts it.
                    self._quiet = self._quiet + len(piece) if level(piece) < QUIET else 0
                    commit = self._since_commit >= COMMIT_AFTER and self._quiet >= PAUSE
                    self._send_audio(piece, commit)
                if ending:
                    self._end()
                    break
        except Exception as exc:
            if not self._closing and not self.error:
                detail = speech._redact(str(exc), self._key)
                if "certificate verify failed" in detail.lower():
                    self.error = messages.SSL_FAILED
                else:
                    self.error = detail[:80] or messages.REQUEST_FAILED
        finally:
            self.text = self._text()
            if not self.text and not self.error and not self._closing:
                self.error = messages.RECORDING_TOO_LONG if self.limit_hit.is_set() else messages.NO_SPEECH
            self._close()
            # Streamed audio is billed whatever became of the take.
            if self._sent:
                usage.record("speech", LIVE_MODEL, seconds=self._sent / (RATE * WIDTH),
                             keyterms=bool(self._terms), status=usage_status(self),
                             wait=time.monotonic() - self._stopped_at if self._stopped_at else 0,
                             take=self.take)
            self.done.set()

    def _end(self):
        if not self._sent:
            return
        self._send({"message_type": "input_audio_chunk", "audio_base_64": "",
                    "commit": True, "sample_rate": RATE})
        mark = len(self._committed)
        # The last commit answers with its transcript, an empty one when
        # nothing was said since the one before.
        deadline = speech._now() + (8 if self._partial or self._since_commit_audio() else 2)
        while speech._now() < deadline and not self._closing and not self.error:
            self._drain(0.05)
            if len(self._committed) > mark:
                return

    def _since_commit_audio(self):
        return self._since_commit > RATE * WIDTH // 2

    def _send_audio(self, pcm, commit=False):
        self._sent += len(pcm)
        self._since_commit = 0 if commit else self._since_commit + len(pcm)
        self._send({
            "message_type": "input_audio_chunk",
            "audio_base_64": base64.b64encode(pcm).decode("ascii"),
            "commit": commit,
            "sample_rate": RATE,
        })

    def _take(self, timeout):
        try:
            item = self._queue.get(timeout=timeout)
        except queue.Empty:
            return False
        if item is None:
            return None
        blob = bytearray(item)
        while True:
            try:
                extra = self._queue.get_nowait()
            except queue.Empty:
                break
            if extra is None:
                self._queue.put(None)
                break
            blob.extend(extra)
        return bytes(blob)

    def _wait_for(self, kind, timeout):
        deadline = speech._now() + timeout
        while speech._now() < deadline and not self._closing and not self.error:
            message = self._next_message(max(0.0, deadline - speech._now()))
            if message is None:
                continue
            if message.get("message_type") == kind:
                return True
            self._apply(message)
        return False

    def _drain(self, timeout):
        got = False
        while True:
            message = self._next_message(0 if got else timeout)
            if message is None:
                return got
            got = True
            self._apply(message)

    def _apply(self, message):
        kind = message.get("message_type") or ""
        if kind == "partial_transcript":
            self._partial = message.get("text") or ""
        elif kind == "committed_transcript":
            self._committed.append((message.get("text") or "").strip())
            self._partial = ""
        elif kind in LIVE_ERRORS:
            self.error = LIVE_ERRORS[kind]
        elif kind.endswith("error") or kind in ("invalid_request", "resource_exhausted", "queue_overflow",
                                                "chunk_size_exceeded", "insufficient_audio_activity"):
            detail = message.get("error") or message.get("message") or kind
            self.error = speech._redact(str(detail), self._key)[:80]

    def preview(self):
        return self._text()

    def _text(self):
        heard = " ".join(piece for piece in self._committed if piece)
        if self._partial.strip():
            heard = (heard + " " + self._partial.strip()).strip()
        return heard

    def _send(self, payload):
        speech._send_frame(self._sock, 1, json.dumps(payload).encode("utf-8"))

    def _next_message(self, timeout):
        payload = speech._read_message(self._sock, self._buf, timeout)
        if payload is None:
            return None
        if not payload:
            return {}
        return json.loads(payload.decode("utf-8"))

    def _close(self):
        sock = self._sock
        self._sock = None
        if sock is None:
            return
        try:
            speech._send_frame(sock, 8, b"")
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass


def usage_status(session):
    """How a streamed take ended, for the usage log."""
    if session._closing:
        return "cancelled"
    if textproc.clean(session.text):
        return "done"
    if session.error and session.error != messages.NO_SPEECH:
        return "failed"
    return "empty"


def _edit_text(value):
    if isinstance(value, dict):
        value = value.get("text") or value.get("edited_text") or ""
    return " ".join(str(value or "").split())


def _edited(edit, heard, edited):
    if not edit or not heard:
        return heard
    kind = edit[0]
    if kind == "translate":
        if not edited:
            raise RuntimeError(messages.TRANSLATE_FAILED)
        return edited
    return textproc.accept_correction(heard, edited)
