# Local HTML evidence reports

The experimental `gramlab.reports` module writes a self-contained HTML file from explicitly
supplied scenario results. It preserves structured JSON evidence, run identity, seed, execution
mode, profile, findings, millisecond timings and original Android PNG captures. This is an
original MIT implementation; it does not recreate the client UI or execute a scenario.

## Try it

After [environment provisioning](environment.md), run the documentation example:

```sh
mkdir -p artifacts
nix develop --command python examples/report.py artifacts/example-report.html
```

Open the resulting file in a browser. The example is labeled incomplete because no bot or
Android client runs. Choose a new output filename on subsequent runs: existing artifacts are
never replaced. There is no report CLI or stable scenario SDK yet.

From Python:

```python
from pathlib import Path
from gramlab.reports import Report, write_report

write_report(
    Path("artifacts/my-report.html"),
    Report(
        run_id="example-7",
        title="A synthetic conversation",
        mode="simulation-only",
        outcome="incomplete",
        seed=7,
        profile={"Source": "Documentation fixture"},
        evidence={"Message": {"chat_id": 1, "text": "سلام hello"}},
        limitations=["Documentation fixture; no scenario assertions ran."],
    ),
)
```

`Finding` records use `observed`, `proposed`, `applied` or `verified` stages. `Screenshot` takes
a caption and PNG bytes, never an arbitrary path from recorded conversation data. Timing labels
must describe what was measured; values are finite, nonnegative milliseconds. Evidence accepts
JSON values with string object keys and at most 50 levels of nesting. The caller supplies the
outcome; writing an HTML file does not verify a scenario or establish Telegram conformance.

## Artifact handling

All supplied text is escaped. JSON remains data, including malicious HTML strings. The page has
no scripts or external resources; a content security policy permits only the embedded stylesheet
by its hash and data images. Native disclosure controls work without JavaScript.

Recognized credential keys, authorization/cookie header lines, token-shaped strings and common
credential assignments are redacted before HTML serialization. Supply additional synthetic
credentials using `write_report(..., secrets=[value])`; exact text and URL-encoded variants are
removed. This is not detection of every possible secret or encoding. Callers must select evidence
that is suitable for retention; source logs and world databases are not modified by the writer.

PNG captures are embedded byte for byte. Validation requires non-interlaced 8-bit RGB/RGBA,
valid checksums and bounded decompression, and rejects unknown metadata chunks and recognized
credential bytes. Limits are eight screenshots, 8 MiB per PNG, 16 million pixels per image and
16 MiB per HTML artifact. There is no OCR or pixel redaction: include only reviewed synthetic
screenshots. These checks do not authorize publication of client-derived assets.

The destination parent must exist. A private temporary file is flushed and published through an
exclusive hard link in the same directory; an existing file or symlink raises `FileExistsError`.
Concurrent writers cannot replace one another's result. The filesystem must support hard links.
Keep generated reports under ignored `artifacts/`, following [offline safety](offline-safety.md).

## Verified integration and limits

The [older-history recovery scenario](android-history-recovery.md) now writes a report after its
semantic assertions pass. Its Android variant adds before-shutdown, recovered and repeated-cold-
restart captures, the copied core source digest, APK digest, client/profile information and
selected guest isolation observations. Both variants retain the bot responses, complete final
history, pending updates, world state and ordered events. The integration helper is test support,
not a generic runtime collector or replay format.

The only timing measurements in this report are Android ActivityManager cold-launch `TotalTime`
values. They exclude guest boot and do not measure bot latency, rendering throughput or injected
delay. Automatic failure collection, consumer log/state hooks, concurrent workload reports,
percentiles and separated latency diagnosis remain open.

Verification: seven report tests cover hostile HTML, credential fixtures, original PNG bytes,
invalid and oversized image data, invalid report values, exclusive publication and racing writers.
The full core gate passes 73 tests at 91.47% statement coverage. A fresh focused Android recovery
test passes and produces all three captures; the unchanged client previously passed all thirteen
Android tests. Browser inspection confirms loaded original images, working disclosure controls,
no external resources and no horizontal overflow at desktop and mobile widths. Report HTML with
malicious text creates no executable DOM nodes.
