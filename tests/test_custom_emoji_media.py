from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

import pytest
from PIL import Image

from gramlab._emoji_media import validate_custom_emoji

ASSETS = Path(__file__).parent / "assets" / "custom-emoji"


def fixture(name: str) -> bytes:
    return (ASSETS / name).read_bytes()


def webp(width: int, height: int, *, frames: int = 1) -> bytes:
    output = io.BytesIO()
    images = [
        Image.new("RGBA", (width, height), (20 * index, 80, 140, 128)) for index in range(frames)
    ]
    images[0].save(
        output,
        format="WEBP",
        lossless=True,
        save_all=frames > 1,
        append_images=images[1:],
        duration=100,
    )
    return output.getvalue()


def test_static_custom_emoji_returns_original_immutable_assets() -> None:
    main = fixture("emoji-static.webp")
    thumbnail = fixture("emoji-thumbnail.webp")

    media = validate_custom_emoji(main, thumbnail)

    assert media.duration_ms == 0
    assert media.main.data is main
    assert (
        media.main.mime_type,
        media.main.extension,
        media.main.width,
        media.main.height,
        media.main.sha256,
    ) == ("image/webp", "webp", 100, 100, hashlib.sha256(main).hexdigest())
    assert media.thumbnail.data is thumbnail
    assert (
        media.thumbnail.mime_type,
        media.thumbnail.extension,
        media.thumbnail.width,
        media.thumbnail.height,
        media.thumbnail.sha256,
    ) == ("image/webp", "webp", 16, 16, hashlib.sha256(thumbnail).hexdigest())


def test_animated_custom_emoji_is_fully_decoded_with_exact_duration() -> None:
    main = fixture("emoji-animated.webm")
    thumbnail = fixture("emoji-thumbnail.webp")

    media = validate_custom_emoji(main, thumbnail)

    assert media.duration_ms == 1000
    assert media.main.data is main
    assert (
        media.main.mime_type,
        media.main.extension,
        media.main.width,
        media.main.height,
        media.main.sha256,
    ) == ("video/webm", "webm", 100, 100, hashlib.sha256(main).hexdigest())


@pytest.mark.parametrize(
    ("main", "thumbnail"),
    [
        (webp(99, 100), fixture("emoji-thumbnail.webp")),
        (fixture("emoji-static.webp"), webp(101, 16)),
        (webp(100, 100, frames=2), fixture("emoji-thumbnail.webp")),
        (fixture("emoji-static.webp"), webp(16, 16, frames=2)),
        (b"\x89PNG\r\n\x1a\ninvalid", fixture("emoji-thumbnail.webp")),
        (fixture("emoji-static.webp"), b"\x89PNG\r\n\x1a\ninvalid"),
        (fixture("emoji-truncated-invalid.webm"), fixture("emoji-thumbnail.webp")),
    ],
)
def test_custom_emoji_rejects_invalid_format_geometry_animation_or_truncation(
    main: bytes, thumbnail: bytes
) -> None:
    with pytest.raises(ValueError):
        validate_custom_emoji(main, thumbnail)


def test_animated_custom_emoji_requires_two_trusted_absolute_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = fixture("emoji-animated.webm")
    thumbnail = fixture("emoji-thumbnail.webp")
    ffmpeg = os.environ["GRAMLAB_FFMPEG"]

    monkeypatch.delenv("GRAMLAB_FFMPEG")
    with pytest.raises(ValueError, match="GRAMLAB_FFMPEG"):
        validate_custom_emoji(main, thumbnail)

    monkeypatch.setenv("GRAMLAB_FFMPEG", ffmpeg)
    monkeypatch.delenv("GRAMLAB_FFPROBE")
    with pytest.raises(ValueError, match="GRAMLAB_FFPROBE"):
        validate_custom_emoji(main, thumbnail)


@pytest.mark.parametrize(
    ("main", "thumbnail"),
    [
        pytest.param(
            b"RIFF" + b"\0" * 4 + b"WEBP" + b"\0" * (512 * 1024 - 11),
            fixture("emoji-thumbnail.webp"),
            id="static-main",
        ),
        pytest.param(
            b"\x1aE\xdf\xa3" + b"\0" * (256 * 1024 - 3),
            fixture("emoji-thumbnail.webp"),
            id="animated-main",
        ),
        pytest.param(
            fixture("emoji-static.webp"),
            b"RIFF" + b"\0" * 4 + b"WEBP" + b"\0" * (128 * 1024 - 11),
            id="thumbnail",
        ),
    ],
)
def test_custom_emoji_rejects_each_input_above_its_byte_limit(
    main: bytes, thumbnail: bytes
) -> None:
    with pytest.raises(ValueError, match="byte limit"):
        validate_custom_emoji(main, thumbnail)
