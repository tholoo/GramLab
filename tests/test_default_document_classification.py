"""Pure contract tests for bounded default document classification."""

import pytest

from gramlab.documents import (
    MAX_DOCUMENT_BYTES,
    DocumentUpload,
    require_supported_default_document,
)


@pytest.mark.parametrize(
    "data,filename",
    [
        (b"GIF87a", "image.bin"),
        (b"GIF89a trailing", "image.bin"),
        (b"RIFFxxxxWEBP", "image.bin"),
        (b"RIFFxxxxWAVE", "audio.bin"),
        (b"RIFFxxxxAVI ", "video.bin"),
        (bytes.fromhex("1a45dfa3"), "media.bin"),
        (b"xxxxftyp", "media.bin"),
        (b"OggS", "audio.bin"),
        (b"fLaC", "audio.bin"),
        (b"ID3", "audio.bin"),
        (bytes.fromhex("1f8b"), r"path\ANIMATED.TgS"),
    ],
)
def test_exact_specialized_signatures_are_rejected(data: bytes, filename: str) -> None:
    upload = DocumentUpload(data, filename, "application/octet-stream")

    with pytest.raises(
        ValueError,
        match=r"^GRAMLAB_UNSUPPORTED: default document content classification$",
    ):
        require_supported_default_document(upload)


@pytest.mark.parametrize(
    "data,filename",
    [
        (b"GIF87", "short.gif"),
        (b"GIF87b", "near.gif"),
        (b"GIF89b", "near.gif"),
        (b"RIFFxxxWEBP", "short.webp"),
        (b"RIFFxxxxWEBQ", "near.webp"),
        (b"RIFFxxxxWAVF", "near.wav"),
        (b"RIFFxxxxAVI!", "near.avi"),
        (bytes.fromhex("1a45dfa2"), "near.webm"),
        (b"xxxftyp", "short.mp4"),
        (b"xxxxftxyp", "near.mp4"),
        (b"OggR", "near.ogg"),
        (b"fLaB", "near.flac"),
        (b"ID4", "near.mp3"),
        (bytes.fromhex("1f"), "short.tgs"),
        (bytes.fromhex("1f8c"), "near.tgs"),
        (bytes.fromhex("1f8b"), "archive.gz"),
        (bytes.fromhex("1f8b"), "animated.tgs.bin"),
    ],
)
def test_short_near_and_generic_gzip_values_remain_documents(data: bytes, filename: str) -> None:
    require_supported_default_document(DocumentUpload(data, filename, "video/mp4"))


@pytest.mark.parametrize(
    "data,filename",
    [
        (b"\x89PNG\r\n\x1a\nbody", "picture.png"),
        (b"\xff\xd8\xffbody", "picture.jpg"),
        (b"%PDF-1.7\nbody", "report.pdf"),
        (b"PK\x03\x04body", "archive.zip"),
        ("متن plain text".encode(), "note.txt"),
        (b"\x00\xff\x10opaque", "unknown.bin"),
    ],
)
def test_general_families_ignore_declared_type_and_remain_documents(
    data: bytes, filename: str
) -> None:
    require_supported_default_document(DocumentUpload(data, filename, "audio/ogg"))


def test_document_size_boundaries_are_unchanged() -> None:
    upload = DocumentUpload(b"x" * MAX_DOCUMENT_BYTES, "maximum.bin")
    require_supported_default_document(upload)

    with pytest.raises(ValueError, match="must not be empty"):
        DocumentUpload(b"", "empty.bin")
    with pytest.raises(ValueError, match="exceeds the 50000000-byte local limit"):
        DocumentUpload(b"x" * (MAX_DOCUMENT_BYTES + 1), "oversized.bin")
