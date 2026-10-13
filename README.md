# Speech Dictation

[Türkçe](README.tr.md)

Dictation and translation for the desktop. Press a shortcut or the floating button, speak, and the text is pasted where you were typing.

Three services listen to you:

| Service | How it listens |
|---|---|
| **Groq** (default) | Whisper Large v3 or Large v3 Turbo, after you stop |
| **ElevenLabs** | Scribe v2 after you stop, or Scribe v2 Realtime while you speak |
| **Gemini** | Gemini 3.5 Transcribe Live, while you speak |

What happens to the text next is your choice, whatever service listened:

| Step | Engines |
|---|---|
| **Correction** (fixes misheard words) | Off, ElevenLabs edit, Groq GPT-OSS 120B / 20B, Gemini Flash-Lite / Flash |
| **Translation** (into any listed language) | ElevenLabs edit, Groq GPT-OSS 120B / 20B, Gemini Flash-Lite / Flash, Google Translate, Gemini Live |

ElevenLabs edit works only on ElevenLabs transcripts and Gemini Live translation only with the Gemini service. You need a key for the service and for each engine you pick; Settings shows only those key fields.

## Features

- **Floating button.** A small always-on-top bar, like Windows voice typing (Win+H). It never takes focus, so the text lands in the window you were typing in. Drag it by any spot outside its buttons; it remembers where it was left.
  - **Microphone:** start or stop dictation.
  - **Language badge** on the microphone's corner (for example `EN`): start or stop translation into that language. It turns blue while translating.
  - **Lock:** keep listening through pauses until you stop it.
  - **✕:** hide the bar (and cancel a running recording). The next dictation brings it back.
- **Auto-stop.** After a few seconds of silence the recording ends and the text is pasted; a ring counts down the last seconds. If nothing is said at all, the recording is dropped and nothing is sent.
- **Sounds.** On Windows, the same start, stop and cancel chimes as Windows voice typing; on macOS and Linux, the app's own chimes in `assets/sounds`.
- **Pause trimming (Groq, ElevenLabs Scribe v2).** Silence before, after and between phrases is cut before upload. This is faster, costs less and keeps the model from inventing text on silence; stock phantom lines such as "Altyazı M.K." are dropped too.
- **Filler words (ElevenLabs).** "um", "uh" and false starts are left out.
- **Smart correction.** The chosen engine fixes words the service misheard, judging by the whole sentence, and leaves everything else alone. If its reply looks like a rewrite, or the request fails, the text is pasted as it was heard.
- **Vocabulary.** Names and terms you use often, such as `Claude`. They go to Whisper as a spelling hint, to ElevenLabs as key terms it listens for, and to the correction and translation engines. Key terms cost extra on ElevenLabs; turn them off in Settings and the correction engine still gets the words.
- **Usage page.** Opens from the tray menu or the Usage button in Settings. It shows, per model, how many requests were made, how much audio, tokens or characters they used and what that costs at list price, for today, the last 7 days, this month, the last 30 days or all time. The summary adds a spending chart, the average wait per model and how much cutting pauses saved. Details lists every request to the second, either one by one or grouped by dictation, with its status (done, nothing heard, cancelled, failed), the wait, and how its cost was worked out; it filters by model and status and exports to CSV. A monthly budget in Settings shows a tray message once the month's estimate passes it. Free tiers and free allowances are not taken off, since the app cannot see whether they still apply, so the figures are estimates; the exact bill is on each provider's page. Only amounts are kept, never the text, in `usage.jsonl` next to `config.json`. The prices live in one table in `speech_dictation/usage.py`.
- **Two interface languages:** English and Turkish. The app follows the system language until you pick one.
- **Start at sign-in**, an option in Settings (a Run entry on Windows, a LaunchAgent on macOS, an autostart entry on Linux).

## Requirements

- Windows 10 or 11, macOS, or Linux (see [macOS and Linux](#macos-and-linux); only Windows has been tested so far)
- Python 3.11 or newer to run from source
- An API key for the service you use:
  - Groq: [console.groq.com/keys](https://console.groq.com/keys)
  - ElevenLabs: [elevenlabs.io/app/developers/api-keys](https://elevenlabs.io/app/developers/api-keys)
  - Gemini: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
  - Google Translate: a Google Cloud API key with the Cloud Translation API turned on. An AI Studio key does not work for it.

## Run from source

```powershell
git clone https://github.com/alican532/speech-dictation.git
cd speech-dictation
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\pythonw launch.py
```

On first start Settings opens and asks for a key. Right-click the tray icon to reach Settings and Quit later.

A desktop shortcut can point at `.venv\Scripts\pythonw.exe` with `launch.py` as its argument and the repo as its working folder.

## Shortcuts

| Action | Default |
|---|---|
| Dictate | `Alt+Z` |
| Translate | none, choose one in Settings |
| Cancel | `Esc` |

Press the shortcut once to start and once more to stop. Clicking the tray icon does the same as the dictation shortcut. Dictation is refused while the Settings window is in front, so the text never lands in one of its fields; click the window you want to type in first.

## macOS and Linux

Every feature is meant to work on all three systems. What differs:

**macOS**
- Allow three permissions in System Settings › Privacy & Security when asked: *Microphone* (to listen), *Accessibility* (to paste with Cmd+V) and *Input Monitoring* (for the global shortcuts).
- The built app is a menu bar app: no Dock icon.
- The floating button is a non-activating panel, so clicking it leaves the app you are typing in at the front. It shows on every Space and over full-screen apps.

**Linux**
- X11: everything works as on Windows.
- Wayland on KDE Plasma or Hyprland: the app asks the compositor to keep the button on top, off the taskbar and unfocused. Dragging is handed to the compositor, so the button's position is not remembered between runs; it starts near the bottom middle of the screen.
- Wayland on GNOME and other desktops: these give no way to keep a window unfocused or on top. The shortcuts work as usual. A dictation started by clicking the button copies the text and asks you to press Ctrl+V, because the click moved the focus to the button.
- Pasting on Wayland goes through `/dev/uinput`, `ydotool` / `wtype`, or the desktop's remote-input permission, in that order.

## Settings

Only what the chosen service and engines use shows.

| Section | Settings |
|---|---|
| Service | Groq Whisper Large v3 / Large v3 Turbo, ElevenLabs Scribe v2 / Scribe v2 Realtime, Gemini Live |
| API keys | Groq, ElevenLabs, Gemini, Google: the ones in use |
| Speech | The language you speak, vocabulary, pause trimming, filler words, ElevenLabs key terms |
| Text | Correction engine, translation engine, translation language |
| General | App language, dictate / translate / cancel shortcuts, auto-stop, sounds, start at sign-in |

Settings are stored here:

| System | Config |
|---|---|
| Windows | `%APPDATA%\SpeechDictation\config.json` |
| macOS | `~/Library/Application Support/SpeechDictation/config.json` |
| Linux | `${XDG_CONFIG_HOME:-~/.config}/SpeechDictation/config.json` |

On first start a config left by the original GeminiSpeechAPI app is copied over once.

## Costs and privacy

- **Groq:** Whisper Large v3 is about $0.111 per audio hour and Turbo about $0.04; each request is billed for at least 10 seconds. GPT-OSS text calls cost a fraction of a cent. There is a rate-limited free tier.
- **ElevenLabs:** Scribe v2 is about $0.22 and Scribe v2 Realtime about $0.39 per audio hour. Vocabulary key terms add about 20% (you can turn them off), ElevenLabs edit adds 30% (billed for at least 10 seconds). The free plan includes a few hours a month.
- **Gemini:** free of charge on the free tier, where Google may use the content to improve its products. On the paid tier, dictation is about $0.009 and translation about $0.037 per minute. Gemini Flash-Lite and Flash text calls cost a fraction of a cent.
- **Google Translate:** $20 per million characters, the first 500,000 characters a month free.

Check the providers' pricing pages for current figures; the usage page adds up your own use at these prices. Audio goes only to the service you pick, and the text only to the engines you pick; the app has no server of its own.

## Building an installer

```powershell
.venv\Scripts\python -m pip install pyinstaller
.venv\Scripts\python packaging\build.py
```

Windows also needs [Inno Setup 6](https://jrsoftware.org/isinfo.php). The result is `dist\SpeechDictation-Setup.exe`, a per-user install. On macOS it is `dist/SpeechDictation-macos.dmg`; on Linux `dist/SpeechDictation-linux.tar.gz`, installed with `./SpeechDictation/install.sh`. Publishing a GitHub release runs the same build in `.github/workflows/release.yml` for Windows, macOS and Linux.

An installed build checks this repo's latest release a few seconds after it starts and every six hours, and updates itself. A copy run from source never updates itself. While the repo is private, GitHub does not answer that check without a token, so installed builds stay on their version.

## Origin

This project began as a copy of [ruwiss/gemini_speech](https://github.com/ruwiss/gemini_speech) and went its own way from version 2.0.0. That repository has no license, so this one stays private.
