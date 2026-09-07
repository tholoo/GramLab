# Validate static and animated custom-emoji media

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: none

Own this ticket, new `src/gramlab/_emoji_media.py` and new `tests/test_custom_emoji_media.py`.
Follow the media interface and exact limits in
[the implementation contract](../../../docs/development/custom-emoji-implementation-contract.md).
Do not modify World, scenario/control, bridge, native patches, existing photo validators, fixtures,
Nix profiles, dependency locks or shared docs. Coordinator supplies portable FFmpeg provisioning.

Implement `validate_custom_emoji(main: bytes, thumbnail: bytes) -> EmojiMedia` with immutable
`main: ImageAsset`, `thumbnail: ImageAsset`, `duration_ms: int`. Full actual Pillow/WebM decoding
must establish valid bytes, dimensions, duration/frame constraints and preserve original alpha.
Use only trusted absolute GRAMLAB_FFMPEG/GRAMLAB_FFPROBE paths, never PATH or runtime acquisition.
Reject invalid media before storage; bound process time/output and reap every child. Avoid
thread-unsafe preexec hooks. Inspect actual FFmpeg behavior when deciding timestamp/truncation
checks; report an infeasible frozen requirement rather than silently weakening it.

Write independent red/green tests around this value-producing validation boundary. Include original
fixtures, wrong format/geometry/codec, truncation past a valid prefix, animated WebP, no tools,
audio, duration/frame bounds and both input byte limits. Use actual provisioned executables for
codec acceptance; test helpers may generate original invalid variants in ignored temporary paths.
Preserve fixture files. No network, Android build or guest. Run scoped Ruff/format/strict mypy and
focused pytest in the outer loopback-only guard through this worktree's tools/dev media, selecting
the pinned media toolchain's executable paths into the two trusted variables for the check.

Read AGENTS.md, TESTING.md and parallel-work.md; claim this ticket before changes, verify checkout
imports and tools/worktree check, commit only owned files and hand back a frozen clean tip with
exact red/green evidence. Coordinator owns integration, provisioning and World/native acceptance.
