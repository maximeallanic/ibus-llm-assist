"""What a correction may change, and what is kept to undo it."""
from dataclasses import dataclass

from .boundaries import graphemes

# Share of the original's graphemes a correction may change; above it the model rephrased. Counted in graphemes
# so that one accented letter, one kana or one Arabic letter weighs the same. Calibrated with dev/bench (docs/benchmarks.md).
MAX_EDIT_RATIO = 0.3


def _distance(a: list[str], b: list[str]) -> int:
    """Levenshtein distance between two grapheme sequences."""
    previous = list(range(len(b) + 1))
    for i, ga in enumerate(a, 1):
        current = [i]
        for j, gb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ga != gb)))
        previous = current
    return previous[-1]


def is_light_edit(original: str, corrected: str) -> bool:
    a, b = graphemes(original), graphemes(corrected)
    if not a:
        return False
    return _distance(a, b) / len(a) <= MAX_EDIT_RATIO


@dataclass
class LastCorrection:
    """A correction just applied: corrected replaced original right before the cursor.

    original and corrected both end with the text typed after the sentence while the model read it; sentence is the
    sentence alone, as it was sent for correction.
    """
    sentence: str
    original: str
    corrected: str
