"""A report is an offline, inspectable artifact with safe synthetic evidence."""

import json
import struct
import threading
import zlib
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

import pytest

from gramlab.reports import Report, write_report


class Document(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []
        self.blocks: list[str] = []
        self.in_pre = False
        self.feed(source)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs)))
        if tag == "pre":
            self.in_pre = True
            self.blocks.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre":
            self.in_pre = False

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self.in_pre:
            self.blocks[-1] += data


def test_report_preserves_complete_evidence_as_text_without_active_html(tmp_path: Path) -> None:
    hostile = (
        '<img src="https://example.invalid/leak" onerror="alert(1)"> سلام & <script>evil()</script>'
    )
    report = Report(
        run_id="recovery-7",
        title="Older reply recovery",
        mode="simulation-only",
        outcome="passed",
        seed=7,
        profile={"core": "experimental", "client": "unavailable"},
        summary="The bot edits an older reply while its observer is stopped.",
        evidence={
            "HTTP exchange": {"method": "editMessageText", "result": {"text": hostile}},
            "World history": [{"id": 2, "chat_id": 1, "sender_id": 2, "text": hostile}],
        },
        limitations=["No Android renderer ran in this mode."],
    )
    target = tmp_path / "report.html"
    assert write_report(target, report) == target
    source = target.read_text()
    document = Document(source)
    visible = "\n".join(document.text)
    for text in [
        "recovery-7",
        "Older reply recovery",
        "simulation-only",
        "passed",
        "HTTP exchange",
        "World history",
        "No Android renderer ran in this mode.",
        "سلام",
    ]:
        assert text in visible
    assert not any(
        tag in {"script", "iframe", "img", "form", "object", "link"} for tag, _ in document.elements
    )
    assert not any(key.startswith("on") for _, attrs in document.elements for key in attrs)
    assert any(
        tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy"
        for tag, attrs in document.elements
    )
    assert [json.loads(block) for block in document.blocks] == list(report.evidence.values())
    assert "&lt;img" in source and "&lt;script&gt;" in source


def test_report_redacts_capabilities_headers_and_registered_consumer_secrets(
    tmp_path: Path,
) -> None:
    bot_token = "2:gramlab_" + "B" * 43
    capability = "gramlab-client_" + "C" * 43
    control = "gramlab-control_" + "D" * 43
    consumer_secret = "synthetic consumer / secret + خصوصی"  # noqa: S105 — deliberate redaction fixture
    report = Report(
        run_id="redaction-7",
        title=f"Failure with {capability} {control}",
        mode="simulation-only",
        outcome="failed",
        seed=7,
        profile={"Authorization": "Bearer private-header"},
        summary=f"POST /bot{bot_token}/sendMessage failed",
        evidence={
            "Request": {
                "headers": {"Cookie": "private-cookie", "X-API-Key": "private-key"},
                "bot_token": bot_token,
                "capability": capability,
                "text": f"{consumer_secret} {quote(consumer_secret, safe='')}",
                "log": "Authorization: Bearer private-log\npassword=private-password\nstatus=400",
                "query": "http://127.0.0.1/?access_token=private-query&offset=2",
            }
        },
        limitations=[f"Consumer-specific secret: {consumer_secret}"],
    )
    target = write_report(tmp_path / "report.html", report, secrets=[consumer_secret])
    source = target.read_text()
    for secret in [
        bot_token,
        capability,
        control,
        consumer_secret,
        quote(consumer_secret, safe=""),
        "private-header",
        "private-cookie",
        "private-key",
        "private-log",
        "private-password",
        "private-query",
    ]:
        assert secret not in source
    request = json.loads(Document(source).blocks[0])
    assert request == {
        "headers": {"Cookie": "[REDACTED]", "X-API-Key": "[REDACTED]"},
        "bot_token": "[REDACTED]",
        "capability": "[REDACTED]",
        "text": "[REDACTED] [REDACTED]",
        "log": "Authorization: [REDACTED]\npassword=[REDACTED]\nstatus=400",
        "query": "http://127.0.0.1/?access_token=[REDACTED]&offset=2",
    }


def pixel_png(raw: bytes = b"\x00\x18\x29\x25", *, width: int = 1, height: int = 1) -> bytes:
    """Original one-pixel RGB fixture, with real PNG CRCs and a compressed scanline."""

    def chunk(kind: bytes, value: bytes) -> bytes:
        return (
            struct.pack(">I", len(value))
            + kind
            + value
            + struct.pack(">I", zlib.crc32(kind + value))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def test_report_embeds_original_screenshots_and_distinguishes_findings_and_timings(
    tmp_path: Path,
) -> None:
    from gramlab.reports import Finding, Screenshot

    png = pixel_png()
    report = Report(
        run_id="android-7",
        title="Recovery",
        mode="headless-android",
        outcome="passed",
        seed=7,
        profile={"Android": "API 36"},
        screenshots=[
            Screenshot(caption="Before <edit>", png=png),
            Screenshot(caption="After restart", png=png),
        ],
        findings=[
            Finding(stage=stage, title=stage + " finding", detail="Older message recovery")
            for stage in ["observed", "proposed", "applied", "verified"]
        ],
        timings={"Android cold launch (ActivityManager)": 1200.5},
    )
    source = write_report(tmp_path / "report.html", report).read_text()
    document = Document(source)
    images = [attrs for tag, attrs in document.elements if tag == "img"]
    assert [image["alt"] for image in images] == ["Before <edit>", "After restart"]
    assert all(
        b64decode(str(image["src"]).removeprefix("data:image/png;base64,")) == png
        for image in images
    )
    visible = "\n".join(document.text)
    for stage in ["observed", "proposed", "applied", "verified"]:
        assert stage + " finding" in visible
    assert "Android cold launch (ActivityManager)" in visible and "1,200.5 ms" in visible
    assert not any(tag in {"script", "link", "iframe"} for tag, _ in document.elements)


def test_invalid_report_data_never_leaves_a_partial_artifact(tmp_path: Path) -> None:
    from gramlab.reports import Finding, Screenshot

    valid = Report(
        run_id="validation",
        title="Validation",
        mode="simulation-only",
        outcome="incomplete",
        seed=7,
        profile={},
    )
    invalid = [
        replace(valid, outcome="success"),
        replace(valid, mode="web"),
        replace(valid, seed=True),
        replace(valid, title="\ud800"),
        replace(valid, profile={"Run": "forged"}),
        replace(valid, evidence={"raw": b"not JSON"}),
        replace(valid, evidence={"non-finite": float("nan")}),
        replace(valid, timings={"launch": -1}),
        replace(valid, timings={"launch": float("inf")}),
        replace(valid, findings=[Finding(stage="assumed", title="Wrong", detail="Invalid stage")]),
        *[
            replace(valid, screenshots=[Screenshot(caption="Invalid", png=value)])
            for value in [
                b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
                pixel_png()[:-1],
                pixel_png() + b"unreviewed metadata",
                b"\x89PNG\r\n\x1a\ninvalid",
                pixel_png().replace(b"IHDR", b"IHDr"),
                pixel_png(b"\x00" * 1_000_000),
                pixel_png(b"\x05\x18\x29\x25"),
                pixel_png(width=0),
                pixel_png(width=16_000_001),
            ]
        ],
    ]
    for index, report in enumerate(invalid):
        target = tmp_path / f"invalid-{index}.html"
        with pytest.raises(ValueError):
            write_report(target, report)
        assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_report_refuses_existing_files_and_symlinks(tmp_path: Path) -> None:
    report = Report(
        run_id="exclusive",
        title="Exclusive",
        mode="simulation-only",
        outcome="incomplete",
        seed=7,
        profile={},
    )
    original = tmp_path / "existing.html"
    original.write_text("previous evidence")
    link = tmp_path / "link.html"
    link.symlink_to(original)
    for target in (original, link):
        with pytest.raises(FileExistsError):
            write_report(target, report)
    assert original.read_text() == "previous evidence"
    assert link.is_symlink()


def test_concurrent_report_writers_publish_one_complete_artifact(tmp_path: Path) -> None:
    ready = threading.Barrier(2)
    target = tmp_path / "report.html"

    def publish(identity: str) -> str | None:
        report = Report(
            run_id=identity,
            title=identity,
            mode="simulation-only",
            outcome="incomplete",
            seed=7,
            profile={},
            evidence={"Owner": identity},
        )
        ready.wait(timeout=5)
        try:
            write_report(target, report)
        except FileExistsError:
            return None
        return identity

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(publish, ["world-alpha", "world-beta"]))
    winners = [value for value in results if value is not None]
    assert len(winners) == 1
    document = Document(target.read_text())
    assert [json.loads(block) for block in document.blocks] == [winners[0]]
    assert all(
        value not in target.read_text() for value in {"world-alpha", "world-beta"} - set(winners)
    )
    assert set(tmp_path.iterdir()) == {target}


def test_large_numeric_evidence_is_retained_without_being_mistaken_for_a_token(
    tmp_path: Path,
) -> None:
    digits = "9" * 100_000
    report = Report(
        run_id="numeric",
        title="Numeric trace",
        mode="simulation-only",
        outcome="incomplete",
        seed=7,
        profile={},
        evidence={"Trace": digits},
    )
    document = Document(write_report(tmp_path / "report.html", report).read_text())
    assert json.loads(document.blocks[0]) == digits
