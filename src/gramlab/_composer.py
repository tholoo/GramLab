"""Independent composer semantics for the experimentally verified plain-text profile.

Native expectations live in tests/fixtures/composer-text.json. This is neither a copy of
the client parser nor a general Markdown implementation. Unestablished syntax is explicit.
"""

from __future__ import annotations

import re
from typing import Any

from gramlab.entities import formatting_entities

_STYLES = {"**": "bold", "__": "italic", "||": "spoiler", "~~": "strikethrough"}
_TOKENS = re.compile(
    r"`(?P<code>[^`]+)`|(?P<delimiter>\*\*|__|\|\||~~)"
    r"(?P<style>[^\r\n\u0085\u2028\u2029]+?)(?P=delimiter)"
)
_LINK = re.compile(r"\w+://|www\.|[\w-]+\.[^\W\d_]{2,}", re.IGNORECASE)
_DICE = {"🎲", "🎯", "🏀", "⚽", "🎳", "🎰"}


def composer_text(value: str) -> dict[str, Any]:
    """Translate one unsplit, unspanned composer input into a semantic text message."""
    if not isinstance(value, str):
        raise ValueError("Composer input must be text")
    try:
        units = len(value.encode("utf-16-le")) // 2
    except UnicodeError:
        raise ValueError("Composer input must contain valid Unicode") from None
    if not 0 < units <= 4096:
        raise ValueError("GRAMLAB_UNSUPPORTED: composer input outside one 4096-unit message")
    text = value.strip(" \n")
    if not text:
        raise ValueError("Composer input contains no message text")
    if "``" in text or _LINK.search(text) or text.rstrip("\ufe0f") in _DICE:
        raise ValueError("GRAMLAB_UNSUPPORTED: fenced/repeated code, links or dice input")
    pieces: list[str] = []
    ranges: list[tuple[str, int, int]] = []
    cursor = 0
    output_length = 0
    for token in _TOKENS.finditer(text):
        literal = text[cursor : token.start()]
        pieces.append(literal)
        output_length += len(literal)
        content = token.group("code")
        kind = "code"
        if content is None:
            content = token.group("style")
            kind = _STYLES[token.group("delimiter")]
        if "`" in content or any(marker in content for marker in _STYLES):
            raise ValueError("GRAMLAB_UNSUPPORTED: interacting composer formatting delimiters")
        pieces.append(content)
        ranges.append((kind, output_length, output_length + len(content)))
        output_length += len(content)
        cursor = token.end()
    pieces.append(text[cursor:])
    expanded = "".join(pieces)
    start = len(expanded) - len(expanded.lstrip(" \n"))
    end = len(expanded.rstrip(" \n"))
    message = expanded[start:end]
    if not message:
        raise ValueError("Composer formatting contains no message text")
    if message.rstrip("\ufe0f") in _DICE or _LINK.search(message):
        raise ValueError("GRAMLAB_UNSUPPORTED: formatting produces a link or dice input")
    entities = []
    for kind, left, right in ranges:
        left, right = max(left, start), min(right, end)
        if left >= right:
            raise ValueError("Composer entity contains no message text")
        entities.append(
            {
                "type": kind,
                "offset": len(expanded[start:left].encode("utf-16-le")) // 2,
                "length": len(expanded[left:right].encode("utf-16-le")) // 2,
            }
        )
    normalized = formatting_entities(message, entities)
    return {"text": message, **({"entities": normalized} if normalized else {})}
