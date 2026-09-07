"""Validation for immutable local custom-emoji media."""

from __future__ import annotations

import hashlib
import io
import json
import os
import selectors
import subprocess
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import IO, Final, cast

from PIL import Image

from gramlab.media import ImageAsset

_WEBM_MAGIC: Final = b"\x1aE\xdf\xa3"
_PROCESS_TIMEOUT_SECONDS: Final = 10.0
_PROBE_OUTPUT_LIMIT: Final = 256 * 1024
_ERROR_OUTPUT_LIMIT: Final = 64 * 1024
_FRAME_BYTES: Final = 100 * 100 * 4
_MAX_FRAMES: Final = 90


@dataclass(frozen=True)
class EmojiMedia:
    main: ImageAsset
    thumbnail: ImageAsset
    duration_ms: int


def _executable(variable: str) -> str:
    value = os.environ.get(variable)
    if value is None:
        raise ValueError(f"{variable} is required for animated custom emoji")
    path = Path(value)
    if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError(f"{variable} must name an absolute executable file")
    return str(path)


def _run_decoder(
    arguments: list[str], data: bytes, *, stdout_limit: int
) -> subprocess.CompletedProcess[bytes]:
    try:
        process = subprocess.Popen(  # noqa: S603
            arguments,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise ValueError("Custom emoji decoder could not start") from error
    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        raise RuntimeError("subprocess pipes were not created")
    input_stream = process.stdin
    output_stream = process.stdout
    error_stream = process.stderr
    streams = (input_stream, output_stream, error_stream)
    selector = selectors.DefaultSelector()
    output = bytearray()
    errors = bytearray()
    offset = 0
    deadline = time.monotonic() + _PROCESS_TIMEOUT_SECONDS
    try:
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
        selector.register(input_stream, selectors.EVENT_WRITE, "stdin")
        selector.register(output_stream, selectors.EVENT_READ, "stdout")
        selector.register(error_stream, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            events = selector.select(remaining)
            if not events:
                raise TimeoutError
            for key, _ in events:
                stream = cast(IO[bytes], key.fileobj)
                if key.data == "stdin":
                    try:
                        written = os.write(stream.fileno(), data[offset : offset + 65_536])
                    except BrokenPipeError:
                        written = 0
                    offset += written
                    if written == 0 or offset == len(data):
                        selector.unregister(stream)
                        stream.close()
                    continue
                chunk = os.read(stream.fileno(), 65_536)
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                destination = output if key.data == "stdout" else errors
                limit = stdout_limit if key.data == "stdout" else _ERROR_OUTPUT_LIMIT
                if len(destination) + len(chunk) > limit:
                    raise OverflowError
                destination.extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        returncode = process.wait(timeout=remaining)
    except TimeoutError as error:
        raise ValueError("Custom emoji decoder timed out") from error
    except subprocess.TimeoutExpired as error:
        raise ValueError("Custom emoji decoder timed out") from error
    except OverflowError as error:
        raise ValueError("Custom emoji decoder output exceeded its limit") from error
    finally:
        selector.close()
        for stream in streams:
            if not stream.closed:
                stream.close()
        if process.poll() is None:
            process.kill()
        process.wait()
    return subprocess.CompletedProcess(arguments, returncode, bytes(output), bytes(errors))


def _validate_webp(data: bytes, *, main: bool) -> ImageAsset:
    maximum = 512 * 1024 if main else 128 * 1024
    label = "main" if main else "thumbnail"
    if not isinstance(data, bytes) or not data or len(data) > maximum:
        raise ValueError(f"Custom emoji {label} exceeds its byte limit")
    try:
        with Image.open(io.BytesIO(data), formats=("WEBP",)) as opened:
            if opened.format != "WEBP":
                raise ValueError(f"Custom emoji {label} must be WebP")
            width, height = opened.size
            if (main and (width, height) != (100, 100)) or (
                not main and not (1 <= width <= 100 and 1 <= height <= 100)
            ):
                raise ValueError(f"Custom emoji {label} has invalid dimensions")
            if getattr(opened, "n_frames", 1) != 1:
                raise ValueError(f"Custom emoji {label} must contain one frame")
            opened.verify()
        with Image.open(io.BytesIO(data), formats=("WEBP",)) as decoded:
            decoded.load()
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(f"Invalid or truncated custom emoji {label}") from error
    return ImageAsset(
        data=data,
        mime_type="image/webp",
        extension="webp",
        width=width,
        height=height,
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _decimal(value: object) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("Custom emoji WebM has invalid timing metadata")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("Custom emoji WebM has invalid timing metadata") from error
    if not result.is_finite():
        raise ValueError("Custom emoji WebM has invalid timing metadata")
    return result


def _validate_webm(data: bytes) -> tuple[ImageAsset, int]:
    if len(data) > 256 * 1024:
        raise ValueError("Custom emoji main exceeds its byte limit")
    ffmpeg = _executable("GRAMLAB_FFMPEG")
    ffprobe = _executable("GRAMLAB_FFPROBE")
    probe = _run_decoder(
        [
            ffprobe,
            "-v",
            "error",
            "-f",
            "matroska",
            "-protocol_whitelist",
            "pipe",
            "-threads",
            "1",
            "-i",
            "pipe:0",
            "-count_frames",
            "-show_entries",
            (
                "stream=index,codec_type,codec_name,width,height,nb_read_frames,r_frame_rate:"
                "stream_tags=alpha_mode:format=format_name,duration:"
                "packet=stream_index,pts_time,duration_time"
            ),
            "-show_packets",
            "-of",
            "json",
        ],
        data,
        stdout_limit=_PROBE_OUTPUT_LIMIT,
    )
    if probe.returncode != 0:
        raise ValueError("Invalid or truncated custom emoji WebM")
    try:
        metadata = json.loads(probe.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Custom emoji probe returned invalid metadata") from error
    if not isinstance(metadata, dict):
        raise ValueError("Custom emoji probe returned invalid metadata")
    streams = metadata.get("streams")
    packets = metadata.get("packets")
    container = metadata.get("format")
    if (
        not isinstance(streams, list)
        or len(streams) != 1
        or not isinstance(packets, list)
        or not isinstance(container, dict)
    ):
        raise ValueError("Custom emoji WebM must contain exactly one stream")
    stream = streams[0]
    if not isinstance(stream, dict) or (
        stream.get("index"),
        stream.get("codec_type"),
        stream.get("codec_name"),
        stream.get("width"),
        stream.get("height"),
    ) != (0, "video", "vp9", 100, 100):
        raise ValueError("Custom emoji WebM must contain one 100x100 VP9 video stream")
    if container.get("format_name") != "matroska,webm":
        raise ValueError("Custom emoji animated main must be WebM")
    tags = stream.get("tags")
    if not isinstance(tags, dict) or tags.get("alpha_mode") != "1":
        raise ValueError("Custom emoji WebM must preserve alpha")
    frame_count_value = stream.get("nb_read_frames")
    try:
        frame_count = int(frame_count_value) if isinstance(frame_count_value, str) else 0
        frame_rate = Fraction(str(stream.get("r_frame_rate")))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError("Custom emoji WebM has invalid frame metadata") from error
    if not 1 <= frame_count <= _MAX_FRAMES or len(packets) != frame_count:
        raise ValueError("Custom emoji WebM has invalid frame count")
    if frame_rate <= 0 or frame_rate > 30:
        raise ValueError("Custom emoji WebM exceeds 30 frames per second")

    expected_timestamp = Decimal(0)
    minimum_frame_duration = Decimal(1) / Decimal(30)
    for packet in packets:
        if not isinstance(packet, dict) or packet.get("stream_index") != 0:
            raise ValueError("Custom emoji WebM has inconsistent packets")
        timestamp = _decimal(packet.get("pts_time"))
        frame_duration = _decimal(packet.get("duration_time"))
        if timestamp != expected_timestamp or frame_duration < minimum_frame_duration:
            raise ValueError("Custom emoji WebM has inconsistent frame timing")
        expected_timestamp += frame_duration
    duration = _decimal(container.get("duration"))
    if duration != expected_timestamp or not Decimal(0) < duration <= Decimal(3):
        raise ValueError("Custom emoji WebM has invalid duration")
    milliseconds = duration * 1000
    if milliseconds != milliseconds.to_integral_value():
        raise ValueError("Custom emoji WebM duration is not an integer millisecond value")

    decoded = _run_decoder(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "matroska",
            "-protocol_whitelist",
            "pipe",
            "-c:v",
            "libvpx-vp9",
            "-threads",
            "1",
            "-i",
            "pipe:0",
            "-map",
            "0:v:0",
            "-an",
            "-sn",
            "-dn",
            "-fps_mode",
            "passthrough",
            "-pix_fmt",
            "rgba",
            "-f",
            "rawvideo",
            "pipe:1",
        ],
        data,
        stdout_limit=_FRAME_BYTES * _MAX_FRAMES,
    )
    if decoded.returncode != 0 or len(decoded.stdout) != frame_count * _FRAME_BYTES:
        raise ValueError("Invalid or truncated custom emoji WebM frames")
    return (
        ImageAsset(
            data=data,
            mime_type="video/webm",
            extension="webm",
            width=100,
            height=100,
            sha256=hashlib.sha256(data).hexdigest(),
        ),
        int(milliseconds),
    )


def validate_custom_emoji(main: bytes, thumbnail: bytes) -> EmojiMedia:
    """Fully decode and validate custom-emoji media from its original bytes."""

    if not isinstance(main, bytes) or not main:
        raise ValueError("Custom emoji main must contain bytes")
    validated_thumbnail = _validate_webp(thumbnail, main=False)
    if main.startswith(_WEBM_MAGIC):
        validated_main, duration_ms = _validate_webm(main)
        return EmojiMedia(validated_main, validated_thumbnail, duration_ms)
    if not (main.startswith(b"RIFF") and main[8:12] == b"WEBP"):
        raise ValueError("Custom emoji main must be WebP or WebM")
    return EmojiMedia(
        main=_validate_webp(main, main=True),
        thumbnail=validated_thumbnail,
        duration_ms=0,
    )
