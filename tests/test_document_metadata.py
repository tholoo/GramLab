"""Pure metadata compatibility against pinned source-derived, independently obtained values."""

import hashlib
import json
from pathlib import Path

import pytest

from gramlab._document_metadata import clean_document_filename, document_mime_type


@pytest.mark.parametrize(
    "original,expected",
    [
        ("", "file"),
        ("dir\\name.tar.gz", "name.tar.gz"),
        ("a/b.pdf", "b.pdf"),
        (".env", "env"),
        (".env.PDF", "env.PDF"),
        ("a.", "a"),
        ("..env", "env"),
        ("dir/", "file"),
        ("...", "file"),
        ("a" * 65 + "." + "b" * 17, "a" * 64 + "." + "b" * 16),
        ("a\ud800b.pdf", "file"),
        ("a\udfffb", "file"),
        ("a" * 65 + "\ud800.pdf", "file"),
    ],
)
def test_cleaned_filename_matches_reviewed_path_bounds_and_invalid_utf8(
    original: str, expected: str
) -> None:
    assert clean_document_filename(original) == expected


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("report.PDF", "application/pdf"),
        ("data.bin", "application/octet-stream"),
        ("notes.txt", "text/plain"),
        ("notes.TEXT", "text/plain"),
        ("no-extension", ""),
        (".pdf", ""),
        ("trailing.", ""),
        ("unknown.gramlab_unknown", ""),
        ("file.\u212amz", ""),
    ],
)
def test_mime_uses_only_pinned_extension_mapping(filename: str, expected: str) -> None:
    assert document_mime_type(filename) == expected


@pytest.mark.parametrize("value", [None, 42, b"name.pdf", ["name.pdf"]])
def test_metadata_rejects_non_strings(value: object) -> None:
    with pytest.raises(TypeError):
        clean_document_filename(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        document_mime_type(value)  # type: ignore[arg-type]


REFERENCE = Path(__file__).parent / "fixtures/document_metadata"


def test_reviewed_unicode_and_truncation_filename_corpus() -> None:
    corpus = json.loads((REFERENCE / "filenames.json").read_text())
    for case in corpus["cases"]:
        assert clean_document_filename(case["input"]) == case["expected"], case["case"]


def test_all_pinned_mime_aliases_and_ascii_case_match_original_generator() -> None:
    reference = json.loads((REFERENCE / "reference.json").read_text())
    assert len(reference["mime"]) == 1005
    for extension, expected in reference["mime"].items():
        assert document_mime_type("file." + extension) == expected
        assert document_mime_type("file." + extension.upper()) == expected
    assert document_mime_type("file.stl") == "application/vnd.ms-pki.stl"
    assert document_mime_type("file.gz") == ""
    assert document_mime_type("file.wmz") == "application/x-ms-wmz"
    assert document_mime_type("file.sub") == "image/vnd.dvb.subtitle"


def test_every_scalar_character_against_independently_executed_cpp_predicates() -> None:
    # The digest was produced by compiled original C++ is_ok/Unicode predicates, not this module.
    # Embedded separators exercise basename parsing separately; surrogates cannot encode as UTF8.
    observed = bytearray(b"\xff" * 0x110000)
    for code in range(0x110000):
        if 0xD800 <= code < 0xE000 or code in (ord("/"), ord("\\")):
            continue
        character = chr(code)
        value = clean_document_filename("a" + character + "b")
        if value == "a" + character + "b":
            observed[code] = 2
        elif value == "ab":
            observed[code] = 0
        else:
            assert value == "a b", hex(code)
            observed[code] = 1
    reference = json.loads((REFERENCE / "reference.json").read_text())
    assert hashlib.sha256(observed).hexdigest() == reference["unicode_public_probe_sha256"]


def test_pinned_new_letter_and_ascii_only_case_matching() -> None:
    # Pinned Python3.13 uses Unicode15.1; TDLib's table admits this newer letter.
    assert clean_document_filename("a\U000105c0b") == "a\U000105c0b"
    assert "\u212amz".lower() == "kmz"
    assert document_mime_type("file.\u212amz") == ""
    assert document_mime_type("file.kmz") == "application/vnd.google-earth.kmz"
