"""The suggestion shown after the cursor. It shrinks while the user types along it and vanishes otherwise."""
from .boundaries import graphemes


class Suggestion:
    def __init__(self) -> None:
        self.text = ''

    def show(self, text: str) -> None:
        self.text = text

    def consume(self, char: str) -> bool:
        """The user typed char: drop it from the front if the suggestion starts with it, else clear."""
        parts = graphemes(self.text)
        if parts and parts[0] == char:
            self.text = ''.join(parts[1:])
            return True
        self.text = ''
        return False

    def take(self) -> str:
        text, self.text = self.text, ''
        return text

    def clear(self) -> None:
        self.text = ''
