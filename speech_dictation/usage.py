"""What each request used, kept on this computer for the Usage window.

Only amounts are written: seconds of audio, tokens and characters, never
the text. Costs are estimates at list prices. Free tiers and free monthly
allowances are left out on purpose: the app cannot see whether they still
apply, so it shows what the use costs at full price.
"""

import json
import os
import threading
import time

from . import paths

PRICES_DATE = "2026-10-12"
# model -> what it costs, in US dollars:
#   hour / minute   per hour or minute of audio
#   minimum         seconds each request is billed for at least
#   keyterms_hour   added per hour when vocabulary words are sent
#   edit_hour       added per hour when ElevenLabs edits the transcript,
#                   billed for at least edit_minimum seconds
#   input / output  per million tokens; thinking counts as output
#   chars           per million characters
#   changes         later prices, as (first day, fields that change)
PRICES = {
    "whisper-large-v3": {"name": "Groq Whisper Large v3", "hour": 0.111, "minimum": 10},
    "whisper-large-v3-turbo": {"name": "Groq Whisper Large v3 Turbo", "hour": 0.04, "minimum": 10},
    "scribe_v2": {"name": "ElevenLabs Scribe v2", "hour": 0.22,
                  "keyterms_hour": 0.05, "edit_hour": 0.07, "edit_minimum": 10},
    "scribe_v2_realtime": {"name": "ElevenLabs Scribe v2 Realtime", "hour": 0.39,
                           "keyterms_hour": 0.08},
    "gemini-3.5-transcribe-live": {"name": "Gemini Live", "minute": 0.009},
    "gemini-3.5-live-translate-preview": {"name": "Gemini Live Translate",
                                          "minute": 0.0368},
    "openai/gpt-oss-120b": {"name": "Groq GPT-OSS 120B", "input": 0.15, "output": 0.60},
    "openai/gpt-oss-20b": {"name": "Groq GPT-OSS 20B", "input": 0.075, "output": 0.30},
    "gemini-3.5-flash-lite": {"name": "Gemini 3.5 Flash-Lite", "input": 0.30, "output": 2.50},
    "gemini-3.8-flash": {"name": "Gemini 3.8 Flash", "input": 0.75, "output": 3.75,
                         "changes": [("2027-01-01", {"input": 1.50, "output": 7.50})]},
    "google-translate": {"name": "Google Translate", "chars": 20.0},
}
KINDS = ("speech", "correct", "translate")

_lock = threading.Lock()


def path():
    return os.path.join(paths.config_dir(), "usage.jsonl")


def model_of(reported):
    """The table entry for a model name a provider reported, or the name itself."""
    reported = (reported or "").replace("models/", "")
    if reported in PRICES:
        return reported
    # Gemini can report a dated build, such as gemini-3.5-flash-lite-001.
    known = [name for name in PRICES if reported.startswith(name)]
    return max(known, key=len) if known else reported


def price(model, day):
    entry = PRICES.get(model)
    if entry is None:
        return None
    entry = dict(entry)
    for first, fields in entry.pop("changes", ()):
        if day >= first:
            entry.update(fields)
    return entry


def cost(model, day, seconds=0.0, tokens_in=0, tokens_out=0, chars=0, keyterms=False, edit=False):
    """Estimated US dollars, or None for a model missing from the table."""
    entry = price(model, day)
    if entry is None:
        return None
    total = 0.0
    if "hour" in entry or "minute" in entry:
        per_second = entry.get("hour", 0) / 3600 + entry.get("minute", 0) / 60
        billed = max(seconds, entry.get("minimum", 0)) if seconds else 0
        total += billed * per_second
        if keyterms:
            total += billed * entry.get("keyterms_hour", 0) / 3600
        if edit:
            total += max(seconds, entry.get("edit_minimum", 0)) * entry.get("edit_hour", 0) / 3600
    total += tokens_in * entry.get("input", 0) / 1e6
    total += tokens_out * entry.get("output", 0) / 1e6
    total += chars * entry.get("chars", 0) / 1e6
    return total


def record(kind, model, seconds=0.0, tokens_in=0, tokens_out=0, chars=0, keyterms=False, edit=False,
           translated=False):
    """Adds one request to the log. Never raises: counting is never worth a lost dictation."""
    try:
        model = model_of(model)
        now = time.time()
        day = time.strftime("%Y-%m-%d", time.localtime(now))
        entry = {"t": round(now, 1), "kind": kind, "model": model}
        if seconds:
            entry["seconds"] = round(seconds, 2)
        if tokens_in or tokens_out:
            entry["in"], entry["out"] = int(tokens_in), int(tokens_out)
        if chars:
            entry["chars"] = int(chars)
        # translated: the speech service translated the take itself.
        extras = [name for name, on in (("keyterms", keyterms), ("edit", edit), ("translated", translated)) if on]
        if extras:
            entry["extras"] = extras
        spent = cost(model, day, seconds, tokens_in, tokens_out, chars, keyterms, edit)
        entry["cost"] = None if spent is None else round(spent, 8)
        line = json.dumps(entry, separators=(",", ":")) + "\n"
        with _lock, open(path(), "a", encoding="utf-8") as handle:
            handle.write(line)
    except Exception:
        pass


def load(since=0.0):
    entries = []
    try:
        with _lock, open(path(), encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return entries
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("t", 0) >= since:
            entries.append(entry)
    return entries


def clear():
    with _lock:
        try:
            os.remove(path())
        except FileNotFoundError:
            pass


def summarize(entries):
    """Rows per model, most expensive first, and the totals."""
    rows = {}
    for entry in entries:
        model = entry.get("model") or "?"
        row = rows.setdefault(model, {
            "model": model, "kinds": [], "requests": 0, "seconds": 0.0,
            "tokens": 0, "chars": 0, "cost": 0.0, "unpriced": 0,
        })
        kinds = [entry.get("kind")] + (["translate"] if "translated" in entry.get("extras", ()) else [])
        for kind in kinds:
            if kind in KINDS and kind not in row["kinds"]:
                row["kinds"].append(kind)
        row["requests"] += 1
        row["seconds"] += entry.get("seconds", 0) or 0
        row["tokens"] += (entry.get("in", 0) or 0) + (entry.get("out", 0) or 0)
        row["chars"] += entry.get("chars", 0) or 0
        if entry.get("cost") is None:
            row["unpriced"] += 1
        else:
            row["cost"] += entry["cost"]
    ordered = sorted(rows.values(), key=lambda row: -row["cost"])
    for row in ordered:
        row["kinds"].sort(key=KINDS.index)
    totals = {
        "cost": sum(row["cost"] for row in ordered),
        "dictations": sum(1 for entry in entries if entry.get("kind") == "speech"),
        "seconds": sum(entry.get("seconds", 0) or 0 for entry in entries if entry.get("kind") == "speech"),
        "unpriced": sum(row["unpriced"] for row in ordered),
    }
    return ordered, totals


def label(model):
    return PRICES.get(model, {}).get("name", model)
