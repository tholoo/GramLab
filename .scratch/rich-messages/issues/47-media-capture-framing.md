# Frame the original ordinary photo and caption completely

Type: bug
Status: ready-for-agent
Work state: resolved
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

## Worker evidence

The probe now derives the usable chat rectangle from the original UI hierarchy: the horizontal
RecyclerView extent, header-control bottom edge and composer top edge. It captures up to seven
bounded attempts, records each XML, original screenshot and parsed geometry, and fails explicitly
if the ordinary photo and caption cannot be placed wholly inside that rectangle. Only the four
established final capture names enter the observation; `initial-top` is byte-for-byte copied from
the successful intermediate capture after media loading has completed.

The retained failing XML parses to a viewport of x=0–320 and y=80–532 and an ordinary target of
x=0–320 and y=0–99, directly preserving the observed clipping evidence. Assertions require both
axes of the successful frame and all intermediate artifacts. Scoped Ruff check/format and mypy
pass. The installed `gramlab` import resolves to this assigned checkout. Per assignment, no APK
build or Android guest was run; coordinator owns native lifecycle acceptance.
