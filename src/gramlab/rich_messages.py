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
}


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


def _text(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if not value:
            raise ValueError("GRAMLAB_UNSUPPORTED: empty rich text arrays")
        return [_text(child) for child in value]
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


def _blocks(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError("GRAMLAB_UNSUPPORTED: rich blocks must be a non-empty array")
    return [_block(block) for block in value]


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
    if kind == "heading":
        if type(obj["size"]) is not int or not 1 <= obj["size"] <= 6:
            raise ValueError("Rich heading size must be between 1 and 6")
        result["size"] = obj["size"]
    if "language" in obj:
        if not isinstance(obj["language"], str):
            raise ValueError("Preformatted language must be a string")
        if obj["language"]:
            result["language"] = obj["language"]
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
