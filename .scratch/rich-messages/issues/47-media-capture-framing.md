# Frame the original ordinary photo and caption completely

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: none

Own this ticket, `tests/probes/android_media.py` and `tests/test_android_media.py` only.
The retained native lifecycle initial-top capture clips the ordinary photo/caption behind the
header. Replace the fixed single swipe with bounded observation-driven framing of the original
message. Use actual UI structure and original screenshots; preserve rendering, fixture content,
profile, timeout policy, semantic/cache/restart assertions and report provenance. Do not assume
one swipe fits every position or claim a toast cause without evidence.

Acceptance: the ordinary photo/caption must lie fully inside the usable chat viewport before
capturing initial-top. Retain intermediate evidence and fail explicitly if the target cannot be
framed in a bounded number of gestures. Keep the real-bot round trip and four final capture names.
The existing clipped retained XML/PNG supplies the observed regression; no synthetic tests that
merely mirror the framing implementation. Run scoped Ruff/format/mypy; coordinator runs the next
native lifecycle gate after integration. No guest or APK build in this worker assignment.
