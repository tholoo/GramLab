from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

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


def padded_webp(data: bytes, size: int) -> bytes:
    payload_size = size - len(data) - 8
    assert payload_size >= 0 and payload_size % 2 == 0
    result = bytearray(data)
    result[4:8] = (size - 8).to_bytes(4, "little")
    result.extend(b"JUNK" + payload_size.to_bytes(4, "little") + bytes(payload_size))
    return bytes(result)


def webm(
    directory: Path,
    *,
    width: int = 100,
    height: int = 100,
    frames: int = 4,
    fps: int = 4,
    alpha: bool = True,
    codec: str = "libvpx-vp9",
    audio: bool = False,
    container: str = "webm",
) -> bytes:
    frame = bytes((30, 120, 220, 128 if alpha else 255)) * (width * height)
    destination = directory / (
        f"generated-{width}-{height}-{frames}-{fps}-{alpha}-{codec}-{audio}.{container}"
    )
    audio_input = ["-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono"] if audio else []
    audio_output = ["-shortest", "-c:a", "libopus"] if audio else ["-an"]
    result = subprocess.run(  # noqa: S603
        [
            os.environ["GRAMLAB_FFMPEG"],
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "-i",
            "pipe:0",
            *audio_input,
            "-frames:v",
            str(frames),
            *audio_output,
            "-c:v",
            codec,
            "-lossless",
            "1",
            "-pix_fmt",
            "yuva420p" if alpha else "yuv420p",
            "-threads",
            "1",
            "-f",
            container,
            "-y",
            str(destination),
        ],
        input=frame * frames,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return destination.read_bytes()


def decoder_script(directory: Path, name: str, body: str) -> str:
    path = directory / name
    path.write_text(f"#!{sys.executable}\n{body}")
    path.chmod(0o700)
    return str(path)


def assert_process_reaped(pid_file: Path) -> None:
    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


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


def test_static_custom_emoji_accepts_both_exact_byte_limits() -> None:
    main = padded_webp(fixture("emoji-static.webp"), 512 * 1024)
    thumbnail = padded_webp(fixture("emoji-thumbnail.webp"), 128 * 1024)

    media = validate_custom_emoji(main, thumbnail)

    assert len(media.main.data) == 512 * 1024
    assert len(media.thumbnail.data) == 128 * 1024


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


@pytest.mark.parametrize("alpha", [False, True])
def test_animated_custom_emoji_accepts_actual_30_fps_with_or_without_alpha(
    tmp_path: Path, alpha: bool
) -> None:
    media = validate_custom_emoji(
        webm(tmp_path, frames=30, fps=30, alpha=alpha), fixture("emoji-thumbnail.webp")
    )

    assert media.duration_ms == 1000


def test_custom_emoji_rejects_matroska_doctype_despite_compatible_stream(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        validate_custom_emoji(webm(tmp_path, container="matroska"), fixture("emoji-thumbnail.webp"))


def test_custom_emoji_rejects_truncation_after_a_complete_valid_webm() -> None:
    main = fixture("emoji-animated.webm") + fixture("emoji-animated.webm")[:64]

    with pytest.raises(ValueError):
        validate_custom_emoji(main, fixture("emoji-thumbnail.webp"))


@pytest.mark.parametrize(
    "options",
    [
        pytest.param({"codec": "libvpx", "alpha": False}, id="vp8-codec"),
        pytest.param({"audio": True}, id="audio-stream"),
        pytest.param({"width": 99}, id="wrong-geometry"),
        pytest.param({"frames": 4, "fps": 1}, id="over-three-seconds"),
        pytest.param({"frames": 31, "fps": 31}, id="over-thirty-fps"),
        pytest.param({"frames": 91, "fps": 30}, id="over-ninety-frames"),
    ],
)
def test_custom_emoji_rejects_actual_webm_stream_constraint_violations(
    tmp_path: Path, options: dict[str, Any]
) -> None:
    with pytest.raises(ValueError):
        validate_custom_emoji(webm(tmp_path, **options), fixture("emoji-thumbnail.webp"))


def test_decoder_output_is_bounded_and_overproducing_child_is_reaped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid_file = tmp_path / "output.pid"
    script = decoder_script(
        tmp_path,
        "noisy-ffprobe",
        """import os
import time
from pathlib import Path

Path(os.environ["GRAMLAB_TEST_PID_FILE"]).write_text(str(os.getpid()))
os.write(1, b"x" * 300_000)
time.sleep(30)
""",
    )
    monkeypatch.setenv("GRAMLAB_TEST_PID_FILE", str(pid_file))
    monkeypatch.setenv("GRAMLAB_FFPROBE", script)

    started = time.monotonic()
    with pytest.raises(ValueError, match="output exceeded"):
        validate_custom_emoji(fixture("emoji-animated.webm"), fixture("emoji-thumbnail.webp"))

    assert time.monotonic() - started < 5
    assert_process_reaped(pid_file)


def test_two_decoders_share_one_ten_second_deadline_and_timeout_child_is_reaped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_ffmpeg = os.environ["GRAMLAB_FFMPEG"]
    real_ffprobe = os.environ["GRAMLAB_FFPROBE"]
    ffmpeg_pid = tmp_path / "ffmpeg.pid"
    ffprobe_pid = tmp_path / "ffprobe.pid"
    wrapper = """import os
import sys
import time
from pathlib import Path

kind = Path(sys.argv[0]).name
Path(os.environ[f"GRAMLAB_TEST_{kind.upper()}_PID"]).write_text(str(os.getpid()))
time.sleep(6)
real = os.environ[f"GRAMLAB_TEST_REAL_{kind.upper()}"]
os.execv(real, [real, *sys.argv[1:]])
"""
    monkeypatch.setenv("GRAMLAB_TEST_FFMPEG_PID", str(ffmpeg_pid))
    monkeypatch.setenv("GRAMLAB_TEST_FFPROBE_PID", str(ffprobe_pid))
    monkeypatch.setenv("GRAMLAB_TEST_REAL_FFMPEG", real_ffmpeg)
    monkeypatch.setenv("GRAMLAB_TEST_REAL_FFPROBE", real_ffprobe)
    monkeypatch.setenv("GRAMLAB_FFMPEG", decoder_script(tmp_path, "ffmpeg", wrapper))
    monkeypatch.setenv("GRAMLAB_FFPROBE", decoder_script(tmp_path, "ffprobe", wrapper))

    started = time.monotonic()
    with pytest.raises(ValueError, match="timed out"):
        validate_custom_emoji(fixture("emoji-animated.webm"), fixture("emoji-thumbnail.webp"))
    elapsed = time.monotonic() - started

    assert 9 <= elapsed < 11.5
    assert_process_reaped(ffprobe_pid)
    assert_process_reaped(ffmpeg_pid)


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

    monkeypatch.setenv("GRAMLAB_FFMPEG", "ffmpeg")
    with pytest.raises(ValueError, match="absolute executable"):
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
