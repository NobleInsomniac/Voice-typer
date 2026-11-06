import threading

from pynput import keyboard
from PyObjCTools import AppHelper

import config
from audio.recorder import Recorder
from cleanup.corrector import Corrector
from output.typer import Typer
from stt.transcriber import Transcriber
from ui.menubar import MenuBarItem
from ui.overlay import Overlay

ALIASES = {
    "right_cmd": "cmd_r",
    "left_cmd": "cmd_l",
    "right_alt": "alt_r",
    "left_alt": "alt_l",
    "right_ctrl": "ctrl_r",
    "left_ctrl": "ctrl_l",
    "right_shift": "shift_r",
    "left_shift": "shift_l",
}


def parse_trigger(name: str):
    name = ALIASES.get(name, name)
    if hasattr(keyboard.Key, name):
        return getattr(keyboard.Key, name)
    if len(name) == 1:
        return keyboard.KeyCode.from_char(name)
    raise ValueError(f"Unknown TRIGGER_KEY: {name!r}")


def main() -> None:
    trigger = parse_trigger(config.TRIGGER_KEY)
    menubar = MenuBarItem(
        f"Hold {config.TRIGGER_KEY} {config.HOLD_TO_START_SECONDS:g}s to start, press to stop"
    )  # keep a reference alive
    recorder = Recorder()
    typer = Typer()
    corrector = Corrector()
    threading.Thread(target=corrector.warmup, daemon=True).start()
    overlay = Overlay(lambda: recorder.level)
    recording = False  # switched on by a long hold, off by the next press
    busy = False  # transcribing: ignore new starts until it has been typed
    key_down = False  # filters out key auto-repeat
    hold_timer = None
    lock = threading.Lock()

    # Load Whisper in the background so the main thread can start servicing UI
    # events right away (otherwise macOS flags the app as "not responding").
    transcriber = None
    ready = threading.Event()

    def load_model() -> None:
        nonlocal transcriber
        print(f"Loading Whisper model '{config.WHISPER_MODEL}'...")
        transcriber = Transcriber()
        ready.set()
        print(
            f"Ready. Hold '{config.TRIGGER_KEY}' for {config.HOLD_TO_START_SECONDS:g}s to start, "
            "press it again to stop."
        )
        overlay.ready()

    threading.Thread(target=load_model, daemon=True).start()

    def process(audio) -> None:
        nonlocal busy
        try:
            text = transcriber.transcribe(audio)
            corrected = corrector.apply(text)
            print(f"> {text}" + (f"\n  -> {corrected}" if corrected != text else ""))
            typer.type_text(corrected)
        finally:
            busy = False
            overlay.hide()

    def start_recording() -> None:
        """Runs on the hold timer once the key has been held long enough."""
        nonlocal recording, hold_timer
        with lock:
            hold_timer = None
            if recording or busy or not key_down:
                return
            recording = True
        recorder.start()
        overlay.show()
        print("Listening... (press the key again to stop)")

    def stop_recording() -> None:
        nonlocal recording, busy
        with lock:
            recording = False
        audio = recorder.stop()
        if len(audio) / config.SAMPLE_RATE < config.MIN_RECORDING_SECONDS:
            overlay.hide()
            return
        busy = True
        overlay.processing()
        threading.Thread(target=process, args=(audio,), daemon=True).start()

    def on_press(key) -> None:
        nonlocal key_down, hold_timer
        if key != trigger:
            # another key during the hold: the trigger is being used as a modifier
            if hold_timer is not None:
                hold_timer.cancel()
                hold_timer = None
            return
        if key_down:
            return  # auto-repeat
        key_down = True
        if recording:
            stop_recording()
        elif busy:
            return
        elif not ready.is_set():
            print("Still loading the model, try again in a moment.")
        else:
            hold_timer = threading.Timer(config.HOLD_TO_START_SECONDS, start_recording)
            hold_timer.daemon = True
            hold_timer.start()

    def on_release(key) -> None:
        nonlocal key_down, hold_timer
        if key != trigger:
            return
        key_down = False
        if hold_timer is not None:  # released too early: a short tap does nothing
            hold_timer.cancel()
            hold_timer = None

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    try:
        AppHelper.runEventLoop(installInterrupt=True)  # real NSApplication loop, on the main thread
    finally:
        listener.stop()


if __name__ == "__main__":
    main()
