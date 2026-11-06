import json
import re
import urllib.request

import config

# Cheap gate: only ask the model when the text contains a possible correction cue.
_CUES = re.compile(
    r"\b(no|nope|actually|i mean|sorry|scratch that|never ?mind|wait|rather|"
    r"make that|correction|change that|strike that|oops|not)\b",
    re.IGNORECASE,
)

_SYSTEM = (
    "You clean up dictated text. If the speaker corrects themselves mid-sentence "
    "(with words like 'no', 'I mean', 'actually', 'sorry', 'scratch that', 'make that', "
    "'wait'), delete the mistaken part and the correction phrase, and keep only the "
    "corrected version in the same sentence. If there is no self-correction, return the "
    "text exactly unchanged. Never add, explain, answer or comment. Output only the final text."
)

_EXAMPLES = [
    ("Change the length to 50 no 60 pixels.", "Change the length to 60 pixels."),
    ("Send it to John, sorry, I mean Mark, by Friday.", "Send it to Mark by Friday."),
    ("Set the color to red, actually blue.", "Set the color to blue."),
    ("Meet me at 5 PM, no wait, 6 PM tomorrow.", "Meet me at 6 PM tomorrow."),
    ("There is no way this will work.", "There is no way this will work."),
    ("I did not say that he was late.", "I did not say that he was late."),
]


class Corrector:
    """Applies spoken self-corrections to transcribed text using a local Ollama model."""

    def __init__(self):
        self.enabled = config.CORRECTION_ENABLED
        self._messages = [{"role": "system", "content": _SYSTEM}]
        for src, dst in _EXAMPLES:
            self._messages += [
                {"role": "user", "content": src},
                {"role": "assistant", "content": dst},
            ]

    def _chat(self, payload: dict, timeout: float) -> dict:
        req = urllib.request.Request(
            config.OLLAMA_URL.rstrip("/") + "/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)

    def warmup(self) -> None:
        """Load the model into memory so the first real correction isn't slow."""
        if not self.enabled:
            return
        try:
            self._chat(
                {"model": config.CORRECTION_MODEL, "messages": [], "keep_alive": "30m"},
                timeout=120,
            )
        except Exception as e:
            print(f"[corrector] warmup failed ({e}); corrections will be skipped if Ollama is down")

    def apply(self, text: str) -> str:
        if not self.enabled or not text or not _CUES.search(text):
            return text
        try:
            data = self._chat(
                {
                    "model": config.CORRECTION_MODEL,
                    "messages": self._messages + [{"role": "user", "content": text}],
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {"temperature": 0, "num_predict": len(text) // 2 + 60},
                },
                timeout=config.CORRECTION_TIMEOUT_SECONDS,
            )
            out = data["message"]["content"].strip().strip('"').strip()
        except Exception as e:
            print(f"[corrector] skipped ({e})")
            return text
        # Safety net: a correction should never add content or blank the message.
        if not out or len(out) > len(text) + 10:
            return text
        return out
