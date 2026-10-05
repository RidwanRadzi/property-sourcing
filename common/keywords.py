"""Shared keyword list for detecting 'unsold developer unit' signals in listing text."""

DEVELOPER_UNIT_KEYWORDS = [
    'developer unit',
    'developer units',
    'direct developer',
    'direct from developer',
    'vp unit',
    'vacant possession unit',
    'developer stock',
    'unsold unit',
    'unsold units',
    'developer price',
    'last few units',
    'below developer price',
]


def text_matches_keyword(text: str) -> str | None:
    """Return the first matching keyword found in text (case-insensitive), or None."""
    if not text:
        return None
    low = text.lower()
    for kw in DEVELOPER_UNIT_KEYWORDS:
        if kw in low:
            return kw
    return None
