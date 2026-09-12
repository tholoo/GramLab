# Representative offline workflow evidence

The public [representative example](../../examples/representative) composes the first operational
milestone in one real local HTTP bot and one scenario. It runs unchanged in simulation or through
the original Telegram Android renderer with bridge version 6. Mini Apps remain deferred.

The workflow includes Persian/English ordinary text; default rich automatic URL/mention detection;
explicit URL, user mention and custom emoji; ordinary and row/inline rich callbacks; callback edits;
a deliberately unacknowledged callback replayed across a bot restart; PNG/JPEG upload, download and
file-ID reuse; default and forced documents; true two-member photo and document albums; and static
WebP plus transparent animated VP9 WebM custom emoji in incoming, content and rich-button carriers.

## Current evidence

The original-client run used the byte-identical example sources committed at `5cbe830`:

- `scenario.py`: `62d3ff47a7113dafe34aa16bf815e5f42d547539e0fcd8b1c0d698c9306eda25`
- `bot.py`: `d1a0cc8e69f693a3abca7f9bccceacd1211b68dff0a796efefd54e166c86f646`
- `assets.py`: `17a3fdfb3226d1dd7287eab19ea2b3f4f0fe8b9a943f7284ef0a3bd01247f7f1`

Its immutable normal31 APK SHA-256 is
`e60a873fc0283b270a35538c63a5f6e701e74cfecb8f10cfce35af670c57be7a`; the runtime-profile
SHA-256 is `fe878c649232bd571a1a64f075a79c11f5db19d30b6e3b04c9573307da83c68f`.
The run used API 36 x86_64, bridge 6, seed 117 and frozen time 1,700,000,000. `result.json` records
`outcome: passed` in 148.200 seconds, 17 final messages, two rich taps, one ordinary tap, two native
composer sends, two edits and five rendered captures. The first bot generation was intentionally
stopped after receiving but not acknowledging its callback; generation 2 received the identical
update, edited/answered it and exited normally after document publication.

The retained self-contained report is
`artifacts/representative-android-03/test_representative_workflow_u0/headless-android/report.html`
(SHA-256 `51b4f40008fcc0e081722b63680534141e6eb8f20158f58b90f8fcabd3a38851`).
It embeds the five original 320×640 PNGs; all were inspected. The complete result alongside it has
SHA-256 `d65888e41fd8f897af5fcccfbcd0cc1297e24c7edf4c5fa4c0783e5f81219048`.
The report contains no host path, consumer identifier, credential or proxy detail.

The guest had zero Android accounts. Its recorded network namespace contained loopback IPv4 and
IPv6 only. World, bot and scenario files were not visible to the app; bot and scenario processes
also rejected visibility of the authoritative World. The final test independently equates scenario
history, retained runner history, reopened World history, bridge-v6 snapshot/change order, every
Bot API message result and every input receipt. Original upload/download bytes and all media,
document and emoji descriptors are hash-pinned.

The native runner itself passed. Its enclosing JUnit records one later test-harness failure because
the first assertion helper restored a redacted accessibility `password=false` field at only one of
its two valid nesting locations. The corrected helper replayed the complete retained native result
successfully; at the user's request, the already successful emulator workflow was not run again.
The simulation test and 17 affected rich-interaction tests pass, and scoped Ruff, formatting and
strict mypy checks pass.

## Aggregate gate context

The pre-example full host gate passed 1,508/1,508 with no skips. The final checkout collects 1,553
non-Android and 74 Android cases. It was not broadly rerun after the user directed that only failed
tests be repeated. The normal31 73-case Android diagnostic passed 68 and failed five; after narrow
fixes, the exact five-case rerun passed four with only the album case failing, and that album case
then passed alone. This is case-level union evidence, not a falsely labeled clean aggregate rerun.
The new 74th Android case is the successful representative runner described above.

This milestone does not claim external Telegram conformance, production custom-emoji entitlement,
HTML parse modes, grouped-media edits, interactive Android mode or Mini Apps.
