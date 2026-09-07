"""Independent validation of the explicitly supported Bot API 10.3 rich block subset."""

from typing import Any

_WRAPPERS = frozenset(
    "bold italic underline strikethrough spoiler subscript superscript marked code".split()
)
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


def _text(value: Any) -> Any:
    if isinstance(value, str):
        return _clean_string(value)
    if isinstance(value, list):
        if not value:
            raise ValueError("GRAMLAB_UNSUPPORTED: empty rich text arrays")
        return [_text(child) for child in value]
    if isinstance(value, dict) and value.get("type") == "button":
        obj = _object(value, {"type", "button"}, set())
        return {"type": "button", "button": _button(obj["button"])}
    obj = _object(value, {"type", "text"}, set())
    if not isinstance(obj["type"], str) or obj["type"] not in _WRAPPERS:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich text type")
    return {"type": obj["type"], "text": _text(obj["text"])}


def _cell(value: Any) -> dict[str, Any]:
    obj = _object(value, set(), {"text", "is_header", "colspan", "rowspan", "align", "valign"})
    result: dict[str, Any] = {}
    if "text" in obj:
        text = _text(obj["text"])
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


def _blocks(value: Any, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError("GRAMLAB_UNSUPPORTED: rich blocks must be a non-empty array")
    return [_block(block) for block in value]


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


def _list_item(value: Any) -> tuple[dict[str, Any], bool]:
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
        "blocks": _blocks(obj["blocks"], allow_empty=True),
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


def _list_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich list items must be a non-empty array")
    converted = [_list_item(item) for item in value]
    if any(ordered != converted[0][1] for _, ordered in converted[1:]):
        raise ValueError("Rich list items must agree on orderedness")
    return [item for item, _ in converted]


def _block(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        raise ValueError("Rich block must be an object with a string type")
    kind = value["type"]
    if kind not in _BLOCK_FIELDS:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich block type")
    required, optional = _BLOCK_FIELDS[kind]
    obj = _object(value, required | {"type"}, optional)
    result: dict[str, Any] = {"type": kind}
    for name in ("text", "summary", "credit", "caption"):
        if name in obj:
            text = _text(obj[name])
            if name not in {"credit", "caption"} or text != "":
                result[name] = text
    if "blocks" in obj:
        result["blocks"] = _blocks(obj["blocks"])
    if kind == "list":
        result["items"] = _list_items(obj["items"])
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
        cells = [[_cell(cell) for cell in row] for row in rows]
        widths = [sum(cell.get("colspan", 1) for cell in row) for row in cells]
        area = sum(cell.get("colspan", 1) * cell.get("rowspan", 1) for row in cells for cell in row)
        if any(width > widths[0] for width in widths[1:]) or area > 10_000:
            raise ValueError("GRAMLAB_UNSUPPORTED: table layout extent")
        result["cells"] = cells
    for name in ("is_bordered", "is_striped", "is_compact", "is_open"):
        _flag(obj, result, name)
    return result


def rich_message(value: Any) -> dict[str, Any]:
    """Validate block input and return a detached official-output-shaped RichMessage.

    Automatic entity detection is not implemented; callers must explicitly disable it.
    Unknown fields and unavailable semantics are rejected before any world mutation.
    """
    _bounded(value)
    obj = _object(value, {"blocks"}, {"is_rtl", "skip_entity_detection"})
    if obj.get("skip_entity_detection") is not True:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich messages require skip_entity_detection=true")
    result: dict[str, Any] = {"blocks": _blocks(obj["blocks"])}
    _flag(obj, result, "is_rtl")
    _bounded(result)
    return result
