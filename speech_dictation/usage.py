"""What each request used, kept on this computer for the Usage window.

Only amounts are written: seconds of audio, tokens and characters, never
the text. Costs are estimates at list prices. Free tiers and free monthly
allowances are left out on purpose: the app cannot see whether they still
apply, so it shows what the use costs at full price.
"""

import csv
import json
import os
import threading
import time
import uuid

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
# done: text came back. empty: nothing was heard. cancelled: stopped by the
# user, though audio already streamed is billed. failed: the request failed;
# a failed upload is not billed, a failed stream is.
STATUSES = ("done", "empty", "cancelled", "failed")

_lock = threading.Lock()


def path():
    return os.path.join(paths.config_dir(), "usage.jsonl")


def new_take():
    """An id shared by the requests of one dictation."""
    return uuid.uuid4().hex[:10]


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


def parts(model, day, seconds=0.0, tokens_in=0, tokens_out=0, chars=0, keyterms=False, edit=False):
    """What the cost is made of, as (what, amount, unit price, unit, dollars), or None."""
    entry = price(model, day)
    if entry is None:
        return None
    out = []
    if seconds and ("hour" in entry or "minute" in entry):
        billed = max(seconds, entry.get("minimum", 0))
        if "hour" in entry:
            out.append(("audio", billed, entry["hour"], "hour", billed * entry["hour"] / 3600))
        else:
            out.append(("audio", billed, entry["minute"], "minute", billed * entry["minute"] / 60))
        if keyterms and entry.get("keyterms_hour"):
            out.append(("keyterms", billed, entry["keyterms_hour"], "hour", billed * entry["keyterms_hour"] / 3600))
        if edit and entry.get("edit_hour"):
            edited = max(seconds, entry.get("edit_minimum", 0))
            out.append(("edit", edited, entry["edit_hour"], "hour", edited * entry["edit_hour"] / 3600))
    if tokens_in and "input" in entry:
        out.append(("input", tokens_in, entry["input"], "million", tokens_in * entry["input"] / 1e6))
    if tokens_out and "output" in entry:
        out.append(("output", tokens_out, entry["output"], "million", tokens_out * entry["output"] / 1e6))
    if chars and "chars" in entry:
        out.append(("chars", chars, entry["chars"], "million", chars * entry["chars"] / 1e6))
    return out


def cost(model, day, seconds=0.0, tokens_in=0, tokens_out=0, chars=0, keyterms=False, edit=False):
    """Estimated US dollars, or None for a model missing from the table."""
    pieces = parts(model, day, seconds, tokens_in, tokens_out, chars, keyterms, edit)
    return None if pieces is None else sum(piece[4] for piece in pieces)


def day_of(entry):
    return time.strftime("%Y-%m-%d", time.localtime(entry.get("t", 0)))


def entry_parts(entry):
    extras = entry.get("extras", ())
    return parts(entry.get("model"), day_of(entry), entry.get("seconds", 0), entry.get("in", 0),
                 entry.get("out", 0), entry.get("chars", 0), "keyterms" in extras, "edit" in extras)


def record(kind, model, seconds=0.0, tokens_in=0, tokens_out=0, chars=0, keyterms=False, edit=False,
           translated=False, recorded=0.0, wait=0.0, status="done", billed=True, take=""):
    """Adds one request to the log. Never raises: counting is never worth a lost dictation.

    recorded: seconds before pauses were cut, when they were. wait: seconds
    from sending to the answer. billed: False for a request the provider
    does not charge, such as one it refused.
    """
    try:
        model = model_of(model)
        now = time.time()
        entry = {"t": round(now, 2), "kind": kind, "model": model, "status": status}
        if take:
            entry["take"] = take
        if seconds:
            entry["seconds"] = round(seconds, 2)
        if recorded and recorded > seconds + 0.05:
            entry["recorded"] = round(recorded, 2)
        if tokens_in or tokens_out:
            entry["in"], entry["out"] = int(tokens_in), int(tokens_out)
        if chars:
            entry["chars"] = int(chars)
        # translated: the speech service translated the take itself.
        extras = [name for name, on in (("keyterms", keyterms), ("edit", edit), ("translated", translated)) if on]
        if extras:
            entry["extras"] = extras
        if wait:
            entry["wait"] = round(wait, 2)
        if billed:
            spent = cost(model, day_of(entry), seconds, tokens_in, tokens_out, chars, keyterms, edit)
            entry["cost"] = None if spent is None else round(spent, 8)
        else:
            entry["cost"] = 0.0
            entry["unbilled"] = True
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
            entry.setdefault("status", "done")
            entries.append(entry)
    return entries


def clear():
    with _lock:
        try:
            os.remove(path())
        except FileNotFoundError:
            pass


def kinds_of(entry):
    kinds = [entry.get("kind")]
    if "translated" in entry.get("extras", ()):
        kinds.append("translate")
    return [kind for kind in kinds if kind in KINDS]


def saved(entry):
    """Dollars that cutting pauses kept off this request."""
    recorded = entry.get("recorded", 0)
    if not recorded or entry.get("unbilled"):
        return 0.0
    extras = entry.get("extras", ())
    whole = cost(entry.get("model"), day_of(entry), recorded, keyterms="keyterms" in extras,
                 edit="edit" in extras)
    if whole is None or entry.get("cost") is None:
        return 0.0
    return max(0.0, whole - entry["cost"])


def summarize(entries):
    """Rows per model, most expensive first, and the totals."""
    rows = {}
    for entry in entries:
        model = entry.get("model") or "?"
        row = rows.setdefault(model, {
            "model": model, "kinds": [], "requests": 0, "seconds": 0.0,
            "tokens": 0, "chars": 0, "cost": 0.0, "unpriced": 0, "waits": [],
        })
        for kind in kinds_of(entry):
            if kind not in row["kinds"]:
                row["kinds"].append(kind)
        row["requests"] += 1
        row["seconds"] += entry.get("seconds", 0) or 0
        row["tokens"] += (entry.get("in", 0) or 0) + (entry.get("out", 0) or 0)
        row["chars"] += entry.get("chars", 0) or 0
        if entry.get("wait") and entry.get("status") == "done":
            row["waits"].append(entry["wait"])
        if entry.get("cost") is None:
            row["unpriced"] += 1
        else:
            row["cost"] += entry["cost"]
    ordered = sorted(rows.values(), key=lambda row: -row["cost"])
    for row in ordered:
        row["kinds"].sort(key=KINDS.index)
        waits = row.pop("waits")
        row["wait"] = sum(waits) / len(waits) if waits else 0.0
    speech = [entry for entry in entries if entry.get("kind") == "speech"]
    totals = {
        "cost": sum(row["cost"] for row in ordered),
        "dictations": len(speech),
        "seconds": sum(entry.get("seconds", 0) or 0 for entry in speech),
        "recorded": sum(entry.get("recorded") or entry.get("seconds", 0) or 0 for entry in speech),
        "saved": sum(saved(entry) for entry in entries),
        "wasted": sum(entry.get("cost") or 0 for entry in entries if entry.get("status") != "done"),
        "unpriced": sum(row["unpriced"] for row in ordered),
    }
    return ordered, totals


def takes(entries):
    """The requests grouped by dictation, newest first."""
    groups = {}
    order = []
    for entry in entries:
        key = entry.get("take") or "t%s" % entry.get("t")
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(entry)
    out = []
    for key in order:
        items = sorted(groups[key], key=lambda entry: entry.get("t", 0))
        speech = next((entry for entry in items if entry.get("kind") == "speech"), items[0])
        kinds = []
        for entry in items:
            for kind in kinds_of(entry):
                if kind not in kinds:
                    kinds.append(kind)
        priced = [entry["cost"] for entry in items if entry.get("cost") is not None]
        out.append({
            "t": items[0].get("t", 0),
            "items": items,
            "kinds": sorted(kinds, key=KINDS.index),
            "status": speech.get("status", "done"),
            "seconds": speech.get("seconds", 0) if speech.get("kind") == "speech" else 0,
            "wait": sum(entry.get("wait", 0) or 0 for entry in items),
            "cost": sum(priced),
            "unpriced": len(items) - len(priced),
        })
    out.sort(key=lambda take: -take["t"])
    return out


def buckets(entries, start, end):
    """Spending per hour for a single day, per day up to two months, per month beyond.

    Returns (unit, [(bucket start, dollars)]).
    """
    span = end - start
    if span <= 86400 + 3600:
        unit = "hour"
    elif span <= 62 * 86400:
        unit = "day"
    else:
        unit = "month"
    edges = []
    moment = _floor(start, unit)
    while moment < end:
        edges.append(moment)
        moment = _step(moment, unit)
    totals = [0.0] * len(edges)
    for entry in entries:
        spent = entry.get("cost") or 0
        stamp = entry.get("t", 0)
        if not edges or stamp < edges[0]:
            continue
        index = len(edges) - 1
        while index > 0 and stamp < edges[index]:
            index -= 1
        totals[index] += spent
    return unit, list(zip(edges, totals))


def _floor(stamp, unit):
    day = time.localtime(stamp)
    if unit == "hour":
        return time.mktime((day.tm_year, day.tm_mon, day.tm_mday, day.tm_hour, 0, 0, 0, 0, -1))
    if unit == "day":
        return time.mktime((day.tm_year, day.tm_mon, day.tm_mday, 0, 0, 0, 0, 0, -1))
    return time.mktime((day.tm_year, day.tm_mon, 1, 0, 0, 0, 0, 0, -1))


def _step(stamp, unit):
    day = time.localtime(stamp)
    if unit == "hour":
        return _floor(stamp + 3600 + 60, "hour")
    if unit == "day":
        # mktime corrects day 32 and a summer time change.
        return time.mktime((day.tm_year, day.tm_mon, day.tm_mday + 1, 0, 0, 0, 0, 0, -1))
    return time.mktime((day.tm_year, day.tm_mon + 1, 1, 0, 0, 0, 0, 0, -1))


def month_start(now=None):
    return _floor(time.time() if now is None else now, "month")


def month_total(now=None):
    return sum(entry.get("cost") or 0 for entry in load(month_start(now)))


def export_csv(entries, target, decimal_comma=False):
    """Writes one row per request. Excel set to Turkish reads ; and a decimal comma."""
    number = (lambda value: ("%s" % value).replace(".", ",")) if decimal_comma else str
    with open(target, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";" if decimal_comma else ",")
        writer.writerow(["time", "dictation", "model", "model_name", "kind", "status", "recorded_s",
                         "sent_s", "tokens_in", "tokens_out", "characters", "extras", "wait_s", "cost_usd"])
        for entry in sorted(entries, key=lambda entry: entry.get("t", 0)):
            cost_value = entry.get("cost")
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("t", 0))),
                entry.get("take", ""),
                entry.get("model", ""),
                label(entry.get("model", "")),
                entry.get("kind", ""),
                entry.get("status", "done"),
                number(entry.get("recorded", entry.get("seconds", ""))) if entry.get("seconds") else "",
                number(entry.get("seconds", "")) if entry.get("seconds") else "",
                entry.get("in", ""),
                entry.get("out", ""),
                entry.get("chars", ""),
                " ".join(entry.get("extras", ())),
                number(entry["wait"]) if entry.get("wait") else "",
                "" if cost_value is None else number("%.8f" % cost_value),
            ])


def label(model):
    return PRICES.get(model, {}).get("name", model)
