"""Typed ordinary document inputs and canonical local identifiers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from gramlab._document_metadata import clean_document_filename, document_mime_type

MAX_DOCUMENT_BYTES = 50_000_000


@dataclass(frozen=True, slots=True)
class DocumentUpload:
    """Caller-owned ordinary bytes plus decoded multipart metadata."""

    data: bytes
    filename: str
    content_type: str | None = None

    def __post_init__(self) -> None:
        if type(self.data) is not bytes:
            raise TypeError("Document data must be bytes")
        if not self.data:
            raise ValueError("Document data must not be empty")
        if len(self.data) > MAX_DOCUMENT_BYTES:
            raise ValueError("Document exceeds the 50000000-byte local limit")
        if not isinstance(self.filename, str):
            raise TypeError("Document filename must be a string")
        if self.content_type is not None and not isinstance(self.content_type, str):
            raise TypeError("Document content_type must be a string or None")

    @property
    def file_name(self) -> str:
        return clean_document_filename(self.filename)

    @property
    def mime_type(self) -> str:
        return document_mime_type(self.file_name)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    @property
    def file_unique_id(self) -> str:
        return _file_unique_id(self.sha256, self.file_name, self.mime_type)


def _file_unique_id(sha256: str, file_name: str, mime_type: str) -> str:
    identity = json.dumps(
        ["document", sha256, file_name, mime_type],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "gramlab_document_unique_" + hashlib.sha256(identity.encode()).hexdigest()


def _storage_fields(upload: DocumentUpload) -> tuple[str, str, str, str]:
    """Derive publication metadata while reading potentially large bytes only once."""
    sha256 = hashlib.sha256(upload.data).hexdigest()
    file_name = clean_document_filename(upload.filename)
    mime_type = document_mime_type(file_name)
    return sha256, file_name, mime_type, _file_unique_id(sha256, file_name, mime_type)


def canonical_document_id(value: Any) -> int:
    """Return a positive signed-64-bit ID from its canonical decimal wire form."""
    if not isinstance(value, str) or re.fullmatch(r"[1-9][0-9]*", value) is None:
        raise ValueError("Invalid document ID")
    identifier = int(value)
    if identifier >= 2**63:
        raise ValueError("Invalid document ID")
    return identifier
