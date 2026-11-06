from pynput.keyboard import Controller


class Typer:
    """Types text into whichever window currently has focus."""

    def __init__(self):
        self._keyboard = Controller()

    def type_text(self, text: str) -> None:
        if text:
            self._keyboard.type(text + " ")
