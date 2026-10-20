"""Unicode text boundaries (graphemes, sentences) computed by Pango, so that no rule depends on one language.

PyGObject misreads PangoLogAttr (a struct of bit fields), so pango_get_log_attrs is called through ctypes and the
bits are read by mask. Offsets are Python code-point offsets, the unit IBus uses for surrounding text.
"""
import ctypes

_pango = ctypes.CDLL('libpango-1.0.so.0')
_pango.pango_language_get_default.restype = ctypes.c_void_p
_pango.pango_get_log_attrs.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
                                       ctypes.c_void_p, ctypes.c_int]
_pango.pango_get_log_attrs.restype = None

# Bit positions in PangoLogAttr (pango-break.h, declaration order of the guint fields).
_CURSOR_POSITION = 1 << 4
_WORD_END = 1 << 6
_SENTENCE_BOUNDARY = 1 << 7
_WORD_BOUNDARY = 1 << 12

# Stand-in for text not typed yet. The end of a text is always a sentence boundary for Pango; appending a
# character that neither continues a sentence nor starts with a lowercase letter (UAX #29 rules SB8 and SB8a)
# keeps only the boundaries the text itself carries. U+FFFC (object replacement) has no sentence property.
_NEXT = '\ufffc'


def _attrs(text: str) -> list[int]:
    """One flag word per position, len(text) + 1 entries."""
    data = text.encode('utf-8')
    n = len(text) + 1
    buf = (ctypes.c_uint32 * n)()
    _pango.pango_get_log_attrs(data, len(data), -1, _pango.pango_language_get_default(), buf, n)
    return list(buf)


def graphemes(text: str) -> list[str]:
    """User-perceived characters of text."""
    if not text:
        return []
    attrs = _attrs(text)
    cuts = [i for i in range(1, len(text)) if attrs[i] & _CURSOR_POSITION] + [len(text)]
    out, start = [], 0
    for cut in cuts:
        out.append(text[start:cut])
        start = cut
    return out


def _sentence_boundaries(text: str) -> list[int]:
    """Offsets inside or at the end of text where a sentence ends, ignoring the boundary at the end of text."""
    attrs = _attrs(text + _NEXT)
    return [i for i in range(1, len(text) + 1) if attrs[i] & _SENTENCE_BOUNDARY]


def ends_sentence(text: str, offset: int) -> bool:
    """Whether a finished sentence ends at offset (trailing spaces belong to the sentence they follow)."""
    return offset in _sentence_boundaries(text[:offset])


def sentence_start_before(text: str, offset: int) -> int:
    """Start of the sentence that ends at offset."""
    starts = [b for b in _sentence_boundaries(text[:offset]) if b < offset]
    return starts[-1] if starts else 0


def cut_at_sentence_end(text: str) -> str:
    """text up to its first sentence end, trailing spaces dropped; the whole text if no sentence ends in it."""
    ends = [b for b in _sentence_boundaries(text) if text[:b].strip()]
    return text[:ends[0]].rstrip() if ends else text


def trim_to_word_end(text: str) -> str:
    """text without its last word, which may be cut short; the whole text if it holds a single word."""
    attrs = _attrs(text)
    ends = [i for i in range(1, len(text)) if attrs[i] & _WORD_END]
    return text[:ends[-1]] if ends else text


def at_word_boundary(text: str, offset: int) -> bool:
    """Whether offset falls between two words (UAX #29) rather than inside one; the end of text always does.

    Scripts written without spaces get the boundaries Pango finds in them: between ideographs for Chinese and
    Japanese, none inside a run of Thai or Lao, which Pango splits only with a dictionary it does not have.
    """
    if offset >= len(text):
        return True
    return bool(_attrs(text)[offset] & _WORD_BOUNDARY)
