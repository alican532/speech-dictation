"""Small HTTPS helpers shared by the providers."""

import json
import os
import urllib.error
import urllib.request

from . import messages
from .speech import _ssl_context

# What each provider's errors read as. A code missing here shows the
# provider's own message.
ERRORS = {
    "groq": {
        401: messages.GROQ_KEY_REJECTED,
        429: messages.GROQ_RATE_LIMIT,
        413: messages.RECORDING_TOO_LONG,
        "offline": messages.GROQ_OFFLINE,
    },
    "elevenlabs": {
        401: messages.ELEVENLABS_KEY_REJECTED,
        429: messages.ELEVENLABS_RATE_LIMIT,
        "offline": messages.ELEVENLABS_OFFLINE,
    },
    "gemini": {
        401: messages.GEMINI_KEY_REJECTED,
        403: messages.GEMINI_KEY_REJECTED,
        429: messages.GEMINI_RATE_LIMIT,
        "offline": messages.GEMINI_OFFLINE,
    },
    "google": {
        401: messages.GOOGLE_KEY_REJECTED,
        403: messages.GOOGLE_KEY_REJECTED,
        429: messages.GOOGLE_RATE_LIMIT,
        "offline": messages.GOOGLE_OFFLINE,
    },
}
NAMES = {"groq": "Groq", "elevenlabs": "ElevenLabs", "gemini": "Gemini", "google": "Google"}


def post(provider, url, body, content_type, headers, timeout=40):
    request = urllib.request.Request(url, data=body, method="POST", headers=dict(headers, **{
        "Content-Type": content_type,
        "User-Agent": "speech-dictation",
    }))
    known = ERRORS[provider]
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as reply:
            return json.loads(reply.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_failure(provider, exc)) from None
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        if "CERTIFICATE_VERIFY_FAILED" in reason:
            raise RuntimeError(messages.SSL_FAILED) from None
        raise RuntimeError(known["offline"]) from None
    except TimeoutError:
        raise RuntimeError(known["offline"]) from None


def post_json(provider, url, payload, headers, timeout=40):
    return post(provider, url, json.dumps(payload).encode("utf-8"), "application/json", headers, timeout)


def multipart(fields, file_name, file_type, file_bytes):
    """Builds a form body. A field given a list is sent once per item."""
    boundary = "----speechdictation%s" % os.urandom(8).hex()
    body = bytearray()
    for name, value in fields:
        for item in value if isinstance(value, (list, tuple)) else [value]:
            body.extend((
                "--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, name, item)
            ).encode("utf-8"))
    body.extend((
        "--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\n"
        "Content-Type: %s\r\n\r\n" % (boundary, file_name, file_type)
    ).encode("ascii"))
    body.extend(file_bytes)
    body.extend(("\r\n--%s--\r\n" % boundary).encode("ascii"))
    return bytes(body), "multipart/form-data; boundary=" + boundary


def _failure(provider, exc):
    known = ERRORS[provider]
    detail = ""
    try:
        data = json.loads(exc.read().decode("utf-8"))
        detail = _detail(data)
    except Exception:
        pass
    if provider == "elevenlabs" and "quota" in detail.lower():
        return messages.ELEVENLABS_QUOTA
    if exc.code in known:
        return known[exc.code]
    if provider == "gemini" and exc.code == 400 and "api key" in detail.lower():
        return messages.GEMINI_KEY_REJECTED
    name = NAMES[provider]
    return ("%s %d: %s" % (name, exc.code, detail))[:80] if detail else "%s error %d" % (name, exc.code)


def _detail(data):
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error.get("status") or "")
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, dict):
        return str(detail.get("message") or detail.get("status") or "")
    if isinstance(detail, list) and detail:
        first = detail[0]
        return str(first.get("msg") if isinstance(first, dict) else first)
    return str(detail or error or "")
