"""Independently specified Bot API formatting ranges; no client schema dependency."""

from typing import Any


def formatting_entities(
    text: str, entities: list[dict[str, Any]] | None
) -> list[dict[str, Any]] | None:
    if entities is None:
        return None
    if not isinstance(entities, list):
        raise ValueError("entities must be an array")
    boundaries = {0}
    position = 0
    for character in text:
        position += 2 if ord(character) > 0xFFFF else 1
        boundaries.add(position)
    normalized: list[dict[str, Any]] = []
    seen = set()
    for entity in entities:
        if not isinstance(entity, dict) or not {"type", "offset", "length"} <= entity.keys():
            raise ValueError("Formatting entity requires type, offset and length")
        kind, offset, length = entity["type"], entity["offset"], entity["length"]
        if not isinstance(kind, str) or kind not in {
            "bold",
            "italic",
            "underline",
            "strikethrough",
            "spoiler",
            "code",
            "pre",
            "blockquote",
            "expandable_blockquote",
        }:
            raise ValueError("GRAMLAB_UNSUPPORTED: formatting entity type")
        if (
            entity.keys()
            - {"type", "offset", "length"}
            - ({"language"} if kind == "pre" else set())
        ):
            raise ValueError("GRAMLAB_UNSUPPORTED: formatting entity fields")
        language = entity.get("language", "")
        if not isinstance(language, str):
            raise ValueError("Preformatted language must be text")
        language.encode("utf-8", errors="strict")
        if (
            type(offset) is not int
            or type(length) is not int
            or length <= 0
            or offset not in boundaries
            or offset + length not in boundaries
        ):
            raise ValueError("Entity range must fit UTF-16 character boundaries")
        key = (kind, offset, length, language)
        if key not in seen:
            seen.add(key)
            record: dict[str, Any] = {"type": kind, "offset": offset, "length": length}
            if language:
                record["language"] = language
            normalized.append(record)
    normalized.sort(key=lambda entity: (entity["offset"], -entity["length"], entity["type"]))
    active: list[dict[str, Any]] = []
    quotations = {"blockquote", "expandable_blockquote"}
    quote_depth = 0
    for entity in normalized:
        start, end = entity["offset"], entity["offset"] + entity["length"]
        while active and active[-1]["offset"] + active[-1]["length"] <= start:
            if active.pop()["type"] in quotations:
                quote_depth -= 1
        if active:
            parent = active[-1]
            if end > parent["offset"] + parent["length"]:
                raise ValueError("Entity ranges must be disjoint or fully nested")
            if entity["type"] in {"code", "pre"} or parent["type"] in {"code", "pre"}:
                raise ValueError("Code entities cannot overlap other formatting")
        if entity["type"] in quotations:
            if quote_depth:
                raise ValueError("Blockquote entities cannot be nested")
            quote_depth += 1
        active.append(entity)
    return normalized or None
