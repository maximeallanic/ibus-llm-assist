"""What the end-to-end run types, per language: the keyboard layout of the nested session, a text beginning to
complete, a sentence with a mistake that the correction must fix, and optional dead-key strokes with the text they
must compose (None when the layout has no dead keys).

The texts are made up for the run. Add a language by adding an entry; nothing else in the run knows the language.
"""
from dataclasses import dataclass

TITLE = 'ibus-llm-assist e2e'  # the client's window title
DEAD_ACUTE, DEAD_GRAVE, DEAD_CIRCUMFLEX = 0xfe51, 0xfe50, 0xfe52


@dataclass(frozen=True)
class Scenario:
    layout: str                  # XKB id of the input source
    beginning: str               # typed, then a pause: a suggestion must show
    faulty: str                  # typed after the accepted suggestion: corrected at its end
    dead_keys: tuple = ()        # keysyms typed last
    composed: str | None = None  # what they must add to the text
    latin: bool = True           # the layout types Latin letters; else Ctrl+Z is pressed by key position


SCENARIOS = {
    'en': Scenario('us', 'Thank you so much for', ' I has a question about the invoice.'),
    'fr': Scenario('fr', 'Bonjour, je voudrais', ' Il a ete tres content.',
                   (0x20, 0x66, DEAD_CIRCUMFLEX, 0x65, 0x74, 0x65), ' fête'),
    'de': Scenario('de', 'Vielen Dank für', ' Ich habe das Buch gelest.'),
    'ar': Scenario('ara', 'شكرا جزيلا على', ' ذهبت الى السوق.', latin=False),
}
