# Prepare an original JPEG input for the required photo workflow

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none for fixtures; runtime media design remains under consultation

The operational milestone requires JPEG as well as PNG. Existing photo fixtures cover PNG only.
Add an original deterministic JPEG and an invalid truncated counterpart, using the pinned optional
media shell. This supplies acceptance inputs for photo upload/reuse and native decoding; it does
not implement or approve media storage, delivery, admission or transformations.

## Assignment

Worker owns this ticket and `tests/assets/rich-media/` on `task/original-jpeg-fixtures`. Keep the
existing PNG generator, verifier, manifest and binary files unchanged. Add separate JPEG tooling,
manifest and two small assets. Shared contributor, CI, handoff and architecture docs belong to the
coordinator. Use the assigned worktree and its `tools/dev`; do not provision another editable install.

The original input is an opaque 64 by 48 RGB image divided into four equal rectangles: top-left
(224,48,48), top-right (48,192,64), bottom-left (48,80,224), bottom-right (224,192,48).
Use the pinned FFmpeg MJPEG encoder, explicit full-range 4:4:4 output, one frame, one thread,
quality 2 and bitexact output. Pin and record the final complete command arguments. Do not acquire
photos or third-party image assets. The invalid input is the first 32 bytes of the valid JPEG.

Use the active generated `GRAMLAB_MEDIA_TOOLCHAIN` and its explicit FFmpeg/ffprobe executable
paths; no host fallback or new toolchain dependency is needed. Record portable package/revision/
version provenance, dimensions, format, validity, SHA-256 and original MIT ownership in a separate
JPEG manifest. Do not commit executable store paths. Keep tooling small and self-contained;
consult the coordinator before moving shared code or changing unrelated fixture interfaces.

## Acceptance

- Repeated guarded generation produces identical bytes and manifest under the pinned profile.
- The generator writes only to an existing non-symlink directory, refuses symlink/nonregular
  destinations and differing existing bytes, and permits identical existing outputs.
- Direct decoding confirms 64 by 48 dimensions, one opaque image and correct quadrant orientation.
  Interior samples eight pixels from each edge must differ by no more than 8 per RGB channel
  from the specified source colors; JPEG is lossy, so do not assert exact encoded RGB equality.
- FFmpeg rejects the truncated header. The coordinator independently checks browser decoding,
  dimensions, opacity, quadrant samples and malformed input from the exact committed blobs.
- Preserve existing PNG hashes and scripts. Run scoped Ruff formatting/lint and strict typing.
  No new runtime pytest inventory, Android guest, dependency upgrade or media API behavior is
  required for this asset task. Use the media shell and existing Linux network namespace guard.
- Record exact checks and original failures in ignored evidence, commit owned files and return
  a clean frozen branch with all task-owned processes terminal for coordinator integration.
