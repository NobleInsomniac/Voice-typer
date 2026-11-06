# voice-typer

Hands-free dictation that runs entirely on your Mac. Hold a key for 2 seconds to start, speak,
press the same key to stop, and the transcribed text is typed into whatever text box is currently focused, in any app.

- **Local speech-to-text** with [faster-whisper](https://github.com/SYSTRAN/faster-whisper). No audio leaves your machine.
- **Self-correction layer**: say "change the length to 50, no, 60 pixels" and the text typed is
  "change the length to 60 pixels." Uses a local [Ollama](https://ollama.com) model.
- **On-screen indicator**: a small pill shows a sound wave that turns into 1s and 0s while you
  speak, and a flickering bit stream while it transcribes. It never steals keyboard focus.

## How it works

```
hold 2s to start ─► press to stop ─► audio/recorder.py ─► stt/transcriber.py ─► cleanup/corrector.py ─► output/typer.py
                       (mic, 16 kHz)        (Whisper)            (Ollama, optional)      (types into focus)
                                 └────────────── ui/overlay.py (indicator) ──────────────┘
```

## Requirements

- **macOS** (the indicator uses AppKit; the typing and key listening use `pynput`)
- Python 3.10+
- [Ollama](https://ollama.com) with a small model, only if you want the correction layer

## Setup

```bash
git clone <your-repo-url> voice-typer
cd voice-typer
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env

# optional, for the self-correction layer
ollama pull llama3.2:3b
```

## Run

```bash
.venv/bin/python main.py
```

The first run downloads the Whisper model. Then click into any text box, hold the trigger key
(Right Command by default) for 2 seconds until the pill appears, speak, then press the key once
more to stop. A quick tap does nothing, and so does using the key as part of a shortcut.

### Double-click app (macOS)

To start it without a terminal, build a launcher app once:

```bash
scripts/build_app.sh            # creates "Voice Typer.app" on your Desktop
```

Double-click it to start. It shows in the Dock with the app icon (right-click → **Quit**, or
Cmd+Q while it is focused) and also adds a microphone icon to the menu bar with **Quit Voice Typer**.
macOS lists it as "Python" in Activity Monitor and Force Quit. Logs go to `~/Library/Logs/voice-typer.log`. Because it is a
separate app, grant it the permissions below the first time (add **Voice Typer** under
Accessibility and Input Monitoring; the microphone prompt appears on first use). Rebuild it if you
move the project folder.

### macOS permissions

Grant your terminal app (Terminal, iTerm, VS Code, ...) these in
**System Settings → Privacy & Security**, then fully quit and reopen it:

- **Microphone**: to record
- **Accessibility**: to type into other apps
- **Input Monitoring**: to detect the trigger key

If text only appears in the terminal, Accessibility is the one that is missing.

## Configuration

Everything lives in `.env` (copy from `.env.example`).

| Variable | Default | Meaning |
|---|---|---|
| `WHISPER_MODEL` | `base.en` | `tiny.en`, `base.en`, `small.en`, `medium.en`, `large-v3`, `distil-small.en`, ... (drop `.en` for multilingual) |
| `WHISPER_DEVICE` | `cpu` | Device for inference |
| `WHISPER_COMPUTE_TYPE` | `int8` | Quantization |
| `WHISPER_LANGUAGE` | `en` | Language code, or empty to auto-detect |
| `TRIGGER_KEY` | `right_cmd` | Key to hold, then press to stop. `right_cmd`, `right_alt`, `right_ctrl`, `right_shift` (and `left_*`), any pynput key name such as `f8`, or a single character |
| `HOLD_TO_START_SECONDS` | `2.0` | How long to hold the trigger key to start recording |
| `MIN_RECORDING_SECONDS` | `0.3` | Shorter recordings are ignored |
| `CORRECTION_ENABLED` | `true` | Turn the self-correction layer on or off |
| `CORRECTION_MODEL` | `llama3.2:3b` | Ollama model used for corrections |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address |
| `CORRECTION_TIMEOUT_SECONDS` | `20` | Give up and type the original text after this long |

Model size is a speed/accuracy trade-off: `base.en` (~150 MB) is fast, `small.en` (~500 MB) is a
good balance, `medium.en` (~1.5 GB) is accurate but slow on CPU.

## Self-correction layer

After transcription, if the text contains a cue word (`no`, `actually`, `I mean`, `sorry`,
`scratch that`, `wait`, ...), a local LLM removes the mistaken part and the correction phrase:

| You say | Typed |
|---|---|
| "Change the length to 50, no, 60 pixels." | Change the length to 60 pixels. |
| "Call Sarah, actually call Priya tomorrow." | Call Priya tomorrow. |
| "Add it to the left, scratch that, to the right." | Add it to the right. |

Text without a cue word is typed instantly. If Ollama is not running, the model is slow, or the
output looks wrong, the original transcription is typed instead. Expect roughly one extra second
when a correction is applied.

## Project layout

```
voice-typer/
├── main.py                 # wires everything together, handles the trigger key
├── config.py               # loads settings from .env
├── audio/recorder.py       # microphone capture
├── stt/transcriber.py      # Whisper speech-to-text
├── cleanup/corrector.py    # self-correction via Ollama
├── output/typer.py         # types text into the focused window
├── ui/overlay.py           # floating on-screen indicator
├── ui/menubar.py           # menu-bar icon with Quit
└── scripts/                # build_app.sh + make_icon.py: double-click launcher
```

## Troubleshooting

- **`Unknown TRIGGER_KEY`**: use a name from the table above.
- **Nothing is typed outside the terminal**: grant Accessibility and restart the terminal.
- **No key detection**: grant Input Monitoring.
- **Corrections never apply**: check `ollama list` and that Ollama is running.
- **Holding Right Command triggers app shortcuts**: pick another trigger, such as `right_alt` or `f8`.

## Licenses

This project does not yet declare a license of its own. Add a `LICENSE` file before publishing if
you want others to be able to reuse it. It depends on the following third-party software, each
under its own license:

| Component | Used for | License |
|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Speech-to-text runtime | MIT |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | Inference engine behind faster-whisper | MIT |
| [OpenAI Whisper models](https://github.com/openai/whisper) | Speech recognition weights | MIT |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) | Microphone capture | MIT |
| [NumPy](https://numpy.org) | Audio arrays | BSD-3-Clause |
| [pynput](https://github.com/moses-palmer/pynput) | Key listening and typing | **LGPL-3.0** |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | `.env` loading | BSD-3-Clause |
| [PyObjC](https://github.com/ronaldoussoren/pyobjc) | On-screen indicator (AppKit) | MIT |
| [Ollama](https://github.com/ollama/ollama) | Local LLM runtime (optional) | MIT |
| [Llama 3.2 3B](https://www.llama.com/llama3_2/license/) | Default correction model (optional) | Llama 3.2 Community License |

pynput is LGPL-3.0: it is installed as an unmodified dependency and not bundled, which that
license allows. The Llama 3.2 model is downloaded separately through Ollama and is subject to
Meta's license and acceptable use policy. Other models you choose (Whisper variants, other Ollama
models) carry their own licenses; check them before redistributing anything.

## Notes

Dictated text is typed with simulated keystrokes, so it goes to whichever window is focused when
transcription finishes. Don't switch windows between releasing the key and the text appearing.
