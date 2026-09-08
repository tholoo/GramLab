"""Multipart upload metadata and unchanged bounded admission."""

from dataclasses import FrozenInstanceError

import pytest

from gramlab.bot_api import _multipart

BOUNDARY = "metadata-boundary"


def multipart(*parts: tuple[list[bytes], bytes], boundary: str = BOUNDARY) -> bytes:
    body = bytearray()
    for headers, payload in parts:
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(b"\r\n".join(headers))
        body.extend(b"\r\n\r\n")
        body.extend(payload)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    return bytes(body)


def disposition(name: str, filename: str | None = None) -> bytes:
    value = f'Content-Disposition: form-data; name="{name}"'
    if filename is not None:
        value += f'; filename="{filename}"'
    return value.encode()


def test_multipart_preserves_complete_upload_metadata_and_exact_bytes() -> None:
    binary = b"\x00\xff\r\n--metadata-boundary-not-a-delimiter\x80"
    raw = multipart(
        ([disposition("chat_id")], "۱۲۳".encode()),
        (
            [
                disposition("document", "گزارش نهایی.bin"),
                b"Content-Type:  Application/X-Custom ; Charset=UTF-8  ",
            ],
            binary,
        ),
        ([disposition("empty-name", ""), b"Content-Type:   "], b""),
        ([disposition("untyped", "plain.dat")], b"\x10\x00tail"),
    )

    fields, uploads = _multipart(raw, f'multipart/form-data; boundary="{BOUNDARY}"')

    assert fields == {"chat_id": "۱۲۳"}
    assert {
        name: (upload.data, upload.filename, upload.content_type)
        for name, upload in uploads.items()
    } == {
        "document": (binary, "گزارش نهایی.bin", "Application/X-Custom ; Charset=UTF-8"),
        "empty-name": (b"", "", ""),
        "untyped": (b"\x10\x00tail", "plain.dat", None),
    }
    with pytest.raises(FrozenInstanceError):
        uploads["document"].filename = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "raw,content_type,error",
    [
        (b"not multipart", f"multipart/form-data; boundary={BOUNDARY}", "body"),
        (
            multipart(([b"Broken"], b"value")),
            f"multipart/form-data; boundary={BOUNDARY}",
            "headers",
        ),
        (
            multipart(
                ([disposition("same")], b"text"),
                ([disposition("same", "file.bin")], b"file"),
            ),
            f"multipart/form-data; boundary={BOUNDARY}",
            "Repeated",
        ),
        (
            multipart(([disposition("file", "file.bin"), b"Content-Type: multipart/mixed"], b"x")),
            f"multipart/form-data; boundary={BOUNDARY}",
            "Nested multipart",
        ),
        (
            multipart(([disposition("text")], b"\xff")),
            f"multipart/form-data; boundary={BOUNDARY}",
            "codec",
        ),
        (
            multipart(([disposition("text")], b"x"), boundary="x" * 71),
            "multipart/form-data; boundary=" + "x" * 71,
            "boundary",
        ),
    ],
)
def test_multipart_rejects_malformed_ambiguous_nested_and_invalid_utf8(
    raw: bytes, content_type: str, error: str
) -> None:
    with pytest.raises((ValueError, UnicodeError), match=error):
        _multipart(raw, content_type)


def test_multipart_retains_existing_part_and_aggregate_size_limits() -> None:
    headers = [disposition("part")]
    too_many = multipart(*[(headers, str(index).encode()) for index in range(65)])
    with pytest.raises(ValueError, match="64 parts"):
        _multipart(too_many, f"multipart/form-data; boundary={BOUNDARY}")

    too_much_text = multipart(([disposition("text")], b"x" * 65_537))
    with pytest.raises(ValueError, match="text fields"):
        _multipart(too_much_text, f"multipart/form-data; boundary={BOUNDARY}")

    too_much_upload = multipart(([disposition("file", "x.bin")], b"x" * 20_000_001))
    with pytest.raises(ValueError, match="file data"):
        _multipart(too_much_upload, f"multipart/form-data; boundary={BOUNDARY}")
