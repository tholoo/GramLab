"""Independent validation of the explicitly supported Bot API 10.3 rich block subset."""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from gramlab.entities import canonical_custom_emoji_id

_WRAPPERS = frozenset(
    "bold italic underline strikethrough spoiler subscript superscript marked code".split()
)
_LINK_FIELDS = {
    "url": "url",
    "email_address": "email_address",
    "phone_number": "phone_number",
}
_BLOCK_FIELDS = {
    "paragraph": ({"text"}, set()),
    "heading": ({"text", "size"}, set()),
    "pre": ({"text"}, {"language"}),
    "footer": ({"text"}, set()),
    "divider": (set(), set()),
    "blockquote": ({"blocks"}, {"credit"}),
    "expandable_blockquote": ({"text"}, {"credit"}),
    "pullquote": ({"text"}, {"credit"}),
    "table": ({"cells"}, {"caption", "is_bordered", "is_striped", "is_compact"}),
    "details": ({"summary", "blocks"}, {"is_open"}),
    "list": ({"items"}, set()),
    "buttons": ({"buttons"}, {"align"}),
    "photo": ({"photo"}, {"caption"}),
}

_LIST_TYPES = frozenset(("a", "A", "i", "I", "1"))
_REMOVED_CHARACTERS = frozenset(
    (
        "\u030a",
        "\u0333",
        "\u033f",
        "\u2028",
        "\u2029",
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",
    )
)
_DIRECTION_MARKERS = frozenset(("\u200e", "\u200f"))
_STRING_STOP_BYTES = 34_996
_BUTTON_ACTIONS = frozenset(("callback_data", "copy_text", "disabled"))
_BUTTON_STYLES = frozenset(("default", "primary", "danger", "success", "link"))
_GENERATED_TEXT_TYPES = frozenset(
    ("mention", "hashtag", "cashtag", "bot_command", "bank_card_number")
)
_CANDIDATE_PRIORITY = {
    "email_address": 0,
    "url": 1,
    "phone_number": 2,
    "mention": 3,
    "hashtag": 4,
    "cashtag": 5,
    "bot_command": 6,
    "bank_card_number": 7,
}
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@(?:[^\W_](?:[\w-]*[^\W_])?\.)+[^\W_](?:[\w-]*[^\W_])?",
    re.UNICODE,
)
_EXPLICIT_URL_RE = re.compile(r"https?://[^\s<>\"\x00-\x1f]+")
_WWW_URL_RE = re.compile(r"www\.[^\s<>\"\x00-\x1f]+")
_BARE_URL_RE = re.compile(
    r"[^\W_](?:[\w-]*[^\W_])?(?:\.[^\W_](?:[\w-]*[^\W_])?)+"
    r"(?:/[^\s<>\"\x00-\x1f]*)?",
    re.UNICODE,
)
_PHONE_RE = re.compile(r"\+[0-9][0-9 ()-]*[0-9]")
_MENTION_RE = re.compile(r"@[A-Za-z][A-Za-z0-9_]{0,31}")
_HASHTAG_RE = re.compile(r"#[\w]{1,64}", re.UNICODE)
_CASHTAG_RE = re.compile(r"\$[A-Z]{1,8}")
_BOT_COMMAND_RE = re.compile(r"/[A-Za-z0-9_]{1,64}(?:@[A-Za-z][A-Za-z0-9_]{0,31})?")
_BANK_CARD_RE = re.compile(r"[0-9](?:[0-9]|[ -](?=[0-9])){11,35}[0-9]")


@dataclass(frozen=True)
class _Candidate:
    start: int
    end: int
    kind: str
    metadata: str | None = None


def _word_character(character: str) -> bool:
    return character == "_" or unicodedata.category(character)[0] in "LMN"


def _candidate_boundaries(value: str, start: int, end: int) -> bool:
    return (start == 0 or not _word_character(value[start - 1])) and (
        end == len(value) or not _word_character(value[end])
    )


def _trim_candidate(value: str) -> str:
    while value and value[-1] in ".,;:!?":
        value = value[:-1]
    pairs = (
        (")", "("),
        ("]", "["),
        ("}", "{"),
        ("\u2019", "\u2018"),
        ("\u201d", "\u201c"),
        ("\u00bb", "\u00ab"),
    )
    changed = True
    while value and changed:
        changed = False
        for closing, opening in pairs:
            if value.endswith(closing) and value.count(closing) > value.count(opening):
                value = value[:-1]
                changed = True
        if value.endswith(('"', "'")) and value.count(value[-1]) % 2:
            value = value[:-1]
            changed = True
        while value and value[-1] in ".,;:!?":
            value = value[:-1]
            changed = True
    return value


def _valid_hostname(hostname: str | None) -> bool:
    if not hostname or len(hostname) > 253 or hostname.startswith(".") or hostname.endswith("."):
        return False
    labels = hostname.split(".")
    if len(labels) < 2:
        return False
    try:
        encoded = [label.encode("idna").decode("ascii") for label in labels]
    except UnicodeError:
        return False
    return all(
        1 <= len(label) <= 63
        and not label.startswith("-")
        and not label.endswith("-")
        and all(
            character.isascii() and (character.isalnum() or character == "-") for character in label
        )
        for label in encoded
    )


def _url_metadata(candidate: str) -> str | None:
    explicit = candidate.startswith(("http://", "https://"))
    target = candidate if explicit else f"https://{candidate}"
    try:
        parsed = urlsplit(target)
        if parsed.scheme not in ("http", "https") or not _valid_hostname(parsed.hostname):
            return None
        # Accessing port performs the standard-library numeric/range validation.
        port = parsed.port
    except ValueError:
        return None
    del port
    if parsed.username is not None or parsed.password is not None:
        return None
    return candidate if explicit else target


def _luhn(value: str) -> bool:
    total = 0
    parity = len(value) % 2
    for index, character in enumerate(value):
        digit = int(character)
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _balanced_parentheses(value: str) -> bool:
    depth = 0
    for character in value:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _add_matches(
    found: list[_Candidate],
    value: str,
    starts: list[int],
    expression: re.Pattern[str],
    kind: str,
) -> None:
    for start in starts:
        match = expression.match(value, start)
        if match is None:
            continue
        displayed = _trim_candidate(match.group())
        if not displayed:
            continue
        end = start + len(displayed)
        if not _candidate_boundaries(value, start, end):
            continue
        metadata: str | None = None
        if kind == "url":
            metadata = _url_metadata(displayed)
            if metadata is None:
                continue
        elif kind == "email_address":
            local, domain = displayed.rsplit("@", 1)
            if len(local) > 64 or not _valid_hostname(domain):
                continue
            metadata = displayed
        elif kind == "phone_number":
            if not _balanced_parentheses(displayed):
                continue
            digits = "".join(
                character for character in displayed if character.isascii() and character.isdigit()
            )
            if not 7 <= len(digits) <= 15:
                continue
            metadata = f"+{digits}"
        elif kind == "hashtag":
            if any(
                character != "_" and unicodedata.category(character)[0] not in "LMN"
                for character in displayed[1:]
            ):
                continue
        elif kind == "bank_card_number":
            digits = displayed.replace(" ", "").replace("-", "")
            if not 13 <= len(digits) <= 19 or not _luhn(digits):
                continue
        found.append(_Candidate(start, end, kind, metadata))


def _select_candidates(found: list[_Candidate]) -> list[_Candidate]:
    ordered = sorted(
        found,
        key=lambda candidate: (
            candidate.start,
            -(candidate.end - candidate.start),
            _CANDIDATE_PRIORITY[candidate.kind],
        ),
    )
    selected: list[_Candidate] = []
    consumed = 0
    for candidate in ordered:
        if candidate.start < consumed:
            continue
        selected.append(candidate)
        consumed = candidate.end
    return selected


def _detected_text(value: str) -> Any:
    found: list[_Candidate] = []
    starts = [
        index for index in range(len(value)) if index == 0 or not _word_character(value[index - 1])
    ]
    for expression, kind in (
        (_EMAIL_RE, "email_address"),
        (_EXPLICIT_URL_RE, "url"),
        (_WWW_URL_RE, "url"),
        (_BARE_URL_RE, "url"),
        (_PHONE_RE, "phone_number"),
        (_MENTION_RE, "mention"),
        (_HASHTAG_RE, "hashtag"),
        (_CASHTAG_RE, "cashtag"),
        (_BOT_COMMAND_RE, "bot_command"),
        (_BANK_CARD_RE, "bank_card_number"),
    ):
        _add_matches(found, value, starts, expression, kind)
    selected = _select_candidates(found)
    if not selected:
        return value
    parts: list[Any] = []
    consumed = 0
    for candidate in selected:
        if candidate.start > consumed:
            parts.append(value[consumed : candidate.start])
        displayed = value[candidate.start : candidate.end]
        node: dict[str, Any] = {"type": candidate.kind, "text": displayed}
        if candidate.kind == "url":
            node["url"] = candidate.metadata
        elif candidate.kind == "email_address":
            node["email_address"] = candidate.metadata
        elif candidate.kind == "phone_number":
            node["phone_number"] = candidate.metadata
        parts.append(node)
        consumed = candidate.end
    if consumed < len(value):
        parts.append(value[consumed:])
    return parts[0] if len(parts) == 1 else parts


def _object(value: Any, required: set[str], optional: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Rich content must be an object")
    if value.keys() - required - optional:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich content fields")
    if required - value.keys():
        raise ValueError("Required rich content field is missing")
    return value


def _flag(value: dict[str, Any], result: dict[str, Any], name: str) -> None:
    if name in value:
        if type(value[name]) is not bool:
            raise ValueError("Rich content flags must be booleans")
        if value[name]:
            result[name] = True


def _bounded(value: Any) -> None:
    # Local implementation limits, not claims about production Telegram acceptance.
    pending = [(value, 0)]
    count = size = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > 32 or count > 10_000:
            raise ValueError("GRAMLAB_UNSUPPORTED: rich content nesting or node limit")
        if isinstance(item, str):
            size += len(item.encode("utf-8", errors="strict"))
            if size > 65_536:
                raise ValueError("GRAMLAB_UNSUPPORTED: rich content UTF-8 byte limit")
            if any(ord(c) < 32 and c not in "\n\t" for c in item):
                raise ValueError("GRAMLAB_UNSUPPORTED: rich text control-character normalization")
        elif isinstance(item, dict):
            if count + len(pending) + 2 * len(item) > 10_000:
                raise ValueError("GRAMLAB_UNSUPPORTED: rich content node limit")
            pending.extend((child, depth + 1) for child in item.values())
            pending.extend((key, depth + 1) for key in item)
        elif isinstance(item, list):
            if count + len(pending) + len(item) > 10_000:
                raise ValueError("GRAMLAB_UNSUPPORTED: rich content node limit")
            pending.extend((child, depth + 1) for child in item)


def _clean_string(value: str) -> str:
    cleaned: list[str] = []
    size = 0
    for character in value:
        if character in _REMOVED_CHARACTERS:
            continue
        if size >= _STRING_STOP_BYTES:
            break
        if character == "\t":
            character = " "
        cleaned.append(character)
        size += len(character.encode("utf-8"))

    for index in range(len(cleaned) - 1):
        if cleaned[index] in _DIRECTION_MARKERS and cleaned[index + 1] in _DIRECTION_MARKERS:
            cleaned[index] = "\u200c"
    return "".join(cleaned)


def _button_label(value: Any) -> Any:
    if isinstance(value, str):
        return _clean_string(value)
    if isinstance(value, dict) and value.get("type") == "custom_emoji":
        obj = _object(value, {"type", "custom_emoji_id", "alternative_text"}, set())
        if not isinstance(obj["alternative_text"], str):
            raise ValueError("Custom emoji alternative text must be a string")
        return {
            "type": "custom_emoji",
            "custom_emoji_id": canonical_custom_emoji_id(obj["custom_emoji_id"]),
            "alternative_text": _clean_string(obj["alternative_text"]),
        }
    if not isinstance(value, list) or not value:
        raise ValueError("Rich button text must be a string or non-empty array")
    return [_button_label(child) for child in value]


def _button(value: Any) -> dict[str, Any]:
    obj = _object(value, {"text"}, {"style"} | _BUTTON_ACTIONS)
    actions = obj.keys() & _BUTTON_ACTIONS
    if len(actions) != 1:
        raise ValueError("Rich button must contain exactly one action")

    result: dict[str, Any] = {"text": _button_label(obj["text"])}
    style = obj.get("style", "")
    if not isinstance(style, str):
        raise ValueError("Rich button style must be a string")
    style = style.lower()
    if style not in _BUTTON_STYLES and style:
        raise ValueError("Invalid rich button style")
    if style not in ("", "default"):
        result["style"] = style

    action = next(iter(actions))
    if action == "callback_data":
        data = obj[action]
        if not isinstance(data, str) or not 1 <= len(data.encode("utf-8")) <= 64:
            raise ValueError("Rich button callback data must contain 1 to 64 UTF-8 bytes")
        result[action] = data
    elif action == "copy_text":
        copy = _object(obj[action], {"text"}, set())
        text = copy["text"]
        if not isinstance(text, str) or not 1 <= len(text) <= 256:
            raise ValueError("Rich button copied text must contain 1 to 256 characters")
        text = _clean_string(text)
        if not 1 <= len(text) <= 256:
            raise ValueError("Cleaned rich button copied text must contain 1 to 256 characters")
        result[action] = {"text": text}
    else:
        disabled = obj[action]
        if not isinstance(disabled, dict) or disabled:
            raise ValueError("Rich button disabled action must be an empty object")
        result[action] = {}

    if style == "link" and action != "callback_data":
        raise ValueError("Link rich button style requires a callback action")
    return result


def _buttons(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError("Rich button rows must contain 1 to 8 buttons")
    return [_button(button) for button in value]


def _text(
    value: Any,
    mention_resolver: Callable[[Any], dict[str, Any]] | None = None,
    *,
    detect: bool = False,
) -> Any:
    if isinstance(value, str):
        cleaned = _clean_string(value)
        return _detected_text(cleaned) if detect else cleaned
    if isinstance(value, list):
        if not value:
            raise ValueError("GRAMLAB_UNSUPPORTED: empty rich text arrays")
        return [_text(child, mention_resolver, detect=detect) for child in value]
    if isinstance(value, dict) and value.get("type") == "custom_emoji":
        obj = _object(value, {"type", "custom_emoji_id", "alternative_text"}, set())
        if not isinstance(obj["alternative_text"], str):
            raise ValueError("Custom emoji alternative text must be a string")
        return {
            "type": "custom_emoji",
            "custom_emoji_id": canonical_custom_emoji_id(obj["custom_emoji_id"]),
            "alternative_text": _clean_string(obj["alternative_text"]),
        }
    if isinstance(value, dict) and value.get("type") == "button":
        obj = _object(value, {"type", "button"}, set())
        return {"type": "button", "button": _button(obj["button"])}
    if isinstance(value, dict) and value.get("type") in _GENERATED_TEXT_TYPES:
        obj = _object(value, {"type", "text"}, set())
        return {
            "type": obj["type"],
            "text": _text(obj["text"], mention_resolver, detect=False),
        }
    if (
        isinstance(value, dict)
        and isinstance(value.get("type"), str)
        and value["type"] in _LINK_FIELDS
    ):
        kind = value["type"]
        metadata = _LINK_FIELDS[kind]
        obj = _object(value, {"type", "text", metadata}, set())
        if not isinstance(obj[metadata], str):
            raise ValueError(f"Rich {kind} metadata must be a string")
        return {
            "type": kind,
            "text": _text(obj["text"], mention_resolver, detect=False),
            metadata: _clean_string(obj[metadata]),
        }
    if isinstance(value, dict) and value.get("type") == "text_mention":
        obj = _object(value, {"type", "text", "user"}, set())
        if mention_resolver is None:
            raise ValueError("GRAMLAB_UNSUPPORTED: rich text mention requires World admission")
        resolved = mention_resolver(obj["user"])
        return {
            "type": "text_mention",
            "text": _text(obj["text"], mention_resolver, detect=False),
            "user_id": resolved["user_id"],
        }
    obj = _object(value, {"type", "text"}, set())
    if not isinstance(obj["type"], str) or obj["type"] not in _WRAPPERS:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich text type")
    return {
        "type": obj["type"],
        "text": _text(obj["text"], mention_resolver, detect=detect and obj["type"] != "code"),
    }


def _cell(
    value: Any,
    mention_resolver: Callable[[Any], dict[str, Any]] | None = None,
    *,
    detect: bool = False,
) -> dict[str, Any]:
    obj = _object(value, set(), {"text", "is_header", "colspan", "rowspan", "align", "valign"})
    result: dict[str, Any] = {}
    if "text" in obj:
        text = _text(obj["text"], mention_resolver, detect=detect)
        if text != "":
            result["text"] = text
    _flag(obj, result, "is_header")
    for name in ("colspan", "rowspan"):
        if name in obj:
            span = obj[name]
            if type(span) is not int or not 0 <= span < 2**31:
                raise ValueError("Table cell spans must be non-negative signed 32-bit integers")
            if span > 100:
                raise ValueError("GRAMLAB_UNSUPPORTED: table span limit")
            if span > 1:
                result[name] = span
    for name, default, choices in (
        ("align", "center" if result.get("is_header") else "left", ("left", "center", "right")),
        ("valign", "middle", ("top", "middle", "bottom")),
    ):
        alignment = obj.get(name, default)
        if alignment not in choices:
            raise ValueError("Invalid table cell alignment")
        result[name] = alignment
    return result


def _blocks(
    value: Any,
    *,
    allow_empty: bool = False,
    photo_resolver: Callable[[Any], dict[str, Any]] | None = None,
    mention_resolver: Callable[[Any], dict[str, Any]] | None = None,
    detect: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError("GRAMLAB_UNSUPPORTED: rich blocks must be a non-empty array")
    return [_block(block, photo_resolver, mention_resolver, detect=detect) for block in value]


def _alphabetic_label(value: int, *, uppercase: bool) -> str:
    letters = []
    offset = ord("A" if uppercase else "a")
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        letters.append(chr(offset + remainder))
    return "".join(reversed(letters))


def _roman_label(value: int, *, uppercase: bool) -> str:
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    parts = []
    for number, numeral in numerals:
        count, value = divmod(value, number)
        parts.append(numeral * count)
    label = "".join(parts)
    return label if uppercase else label.lower()


def _ordered_label(kind: str, value: int) -> str:
    if kind in ("a", "A") and value > 0:
        label = _alphabetic_label(value, uppercase=kind == "A")
    elif kind in ("i", "I") and 0 < value < 4000:
        label = _roman_label(value, uppercase=kind == "I")
    else:
        label = str(value)
    return f"{label}."


def _list_item(
    value: Any,
    photo_resolver: Callable[[Any], dict[str, Any]] | None = None,
    mention_resolver: Callable[[Any], dict[str, Any]] | None = None,
    *,
    detect: bool = False,
) -> tuple[dict[str, Any], bool]:
    obj = _object(
        value,
        {"blocks"},
        {"has_checkbox", "is_checked", "value", "type"},
    )
    kind = obj.get("type", "")
    if not isinstance(kind, str) or (kind and kind not in _LIST_TYPES):
        raise ValueError("Invalid rich list item type")
    number = obj.get("value", 0)
    if type(number) is not int or not -(2**31) <= number < 2**31:
        raise ValueError("Rich list item value must be a signed 32-bit integer")

    ordered = bool(kind)
    result: dict[str, Any] = {
        "label": _ordered_label(kind, number) if ordered else "•",
        "blocks": _blocks(
            obj["blocks"],
            allow_empty=True,
            photo_resolver=photo_resolver,
            mention_resolver=mention_resolver,
            detect=detect,
        ),
    }
    flags: dict[str, Any] = {}
    _flag(obj, flags, "has_checkbox")
    _flag(obj, flags, "is_checked")
    if flags.get("has_checkbox"):
        result["has_checkbox"] = True
        if flags.get("is_checked"):
            result["is_checked"] = True
    if ordered:
        result["type"] = kind
        result["value"] = number
    return result, ordered


def _list_items(
    value: Any,
    photo_resolver: Callable[[Any], dict[str, Any]] | None = None,
    mention_resolver: Callable[[Any], dict[str, Any]] | None = None,
    *,
    detect: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich list items must be a non-empty array")
    converted = [
        _list_item(item, photo_resolver, mention_resolver, detect=detect) for item in value
    ]
    if any(ordered != converted[0][1] for _, ordered in converted[1:]):
        raise ValueError("Rich list items must agree on orderedness")
    return [item for item, _ in converted]


def _block(
    value: Any,
    photo_resolver: Callable[[Any], dict[str, Any]] | None = None,
    mention_resolver: Callable[[Any], dict[str, Any]] | None = None,
    *,
    detect: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        raise ValueError("Rich block must be an object with a string type")
    kind = value["type"]
    if kind not in _BLOCK_FIELDS:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich block type")
    required, optional = _BLOCK_FIELDS[kind]
    obj = _object(value, required | {"type"}, optional)
    result: dict[str, Any] = {"type": kind}
    if kind == "photo":
        if photo_resolver is None:
            raise ValueError("GRAMLAB_UNSUPPORTED: rich photo requires upload resolution")
        result["asset_id"] = photo_resolver(obj["photo"])["asset_id"]
        if "caption" in obj and obj["caption"] is not None:
            caption = rich_caption(obj["caption"], mention_resolver, detect=detect)
            if caption:
                result["caption"] = caption
    for name in ("text", "summary", "credit", "caption"):
        if name == "caption" and kind == "photo":
            continue
        if name in obj:
            text = _text(obj[name], mention_resolver, detect=detect and kind != "pre")
            if name not in {"credit", "caption"} or text != "":
                result[name] = text
    if "blocks" in obj:
        result["blocks"] = _blocks(
            obj["blocks"],
            photo_resolver=photo_resolver,
            mention_resolver=mention_resolver,
            detect=detect,
        )
    if kind == "list":
        result["items"] = _list_items(obj["items"], photo_resolver, mention_resolver, detect=detect)
    if kind == "buttons":
        result["buttons"] = _buttons(obj["buttons"])
        align = obj.get("align", "")
        if not isinstance(align, str) or align not in ("", "left", "center", "right"):
            raise ValueError("Invalid rich button row alignment")
        if align:
            result["align"] = align
    if kind == "heading":
        if type(obj["size"]) is not int or not 1 <= obj["size"] <= 6:
            raise ValueError("Rich heading size must be between 1 and 6")
        result["size"] = obj["size"]
    if "language" in obj:
        if not isinstance(obj["language"], str):
            raise ValueError("Preformatted language must be a string")
        language = _clean_string(obj["language"])
        if language:
            result["language"] = language
    if kind == "table":
        rows = obj["cells"]
        if (
            not isinstance(rows, list)
            or not rows
            or any(not isinstance(row, list) or not row for row in rows)
        ):
            raise ValueError("GRAMLAB_UNSUPPORTED: table cells must contain non-empty rows")
        cells = [[_cell(cell, mention_resolver, detect=detect) for cell in row] for row in rows]
        widths = [sum(cell.get("colspan", 1) for cell in row) for row in cells]
        area = sum(cell.get("colspan", 1) * cell.get("rowspan", 1) for row in cells for cell in row)
        if any(width > widths[0] for width in widths[1:]) or area > 10_000:
            raise ValueError("GRAMLAB_UNSUPPORTED: table layout extent")
        result["cells"] = cells
    for name in ("is_bordered", "is_striped", "is_compact", "is_open"):
        _flag(obj, result, name)
    return result


def rich_caption(
    value: Any,
    mention_resolver: Callable[[Any], dict[str, Any]] | None = None,
    *,
    detect: bool = False,
) -> dict[str, Any]:
    """Normalize the official RichBlockCaption text/credit carrier."""
    obj = _object(value, set(), {"text", "credit"})
    text = "" if obj.get("text") is None else _text(obj["text"], mention_resolver, detect=detect)
    credit = (
        "" if obj.get("credit") is None else _text(obj["credit"], mention_resolver, detect=detect)
    )
    if text == "" and credit == "":
        return {}
    result: dict[str, Any] = {"text": text}
    if credit != "":
        result["credit"] = credit
    return result


def rich_message(
    value: Any,
    photo_resolver: Callable[[Any], dict[str, Any]] | None = None,
    mention_resolver: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate block input and return a detached official-output-shaped RichMessage."""
    _bounded(value)
    obj = _object(value, {"blocks"}, {"is_rtl", "skip_entity_detection"})
    if "skip_entity_detection" in obj and type(obj["skip_entity_detection"]) is not bool:
        raise ValueError("Rich content flags must be booleans")
    detect = obj.get("skip_entity_detection") is not True
    if not isinstance(obj["blocks"], list) or not obj["blocks"]:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich blocks must be a non-empty array")
    result: dict[str, Any] = {
        "blocks": [
            _block(block, photo_resolver, mention_resolver, detect=detect)
            for block in obj["blocks"]
        ]
    }
    _flag(obj, result, "is_rtl")
    _bounded(result)
    return result
