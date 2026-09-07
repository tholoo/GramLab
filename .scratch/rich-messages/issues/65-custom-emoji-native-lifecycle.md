# Observe original custom-emoji rendering, animation and cold-cache reuse

Type: feature
Status: ready-for-agent
Work state: open
Blocked by: ticket63 frozen shared real-bot fixture for integrated execution

Coordinator owns this ticket, new `tests/probes/android_custom_emoji.py`,
`tests/test_android_custom_emoji.py`, optional original pixel-oracle helper/test, and native execution.
A separately assigned worker may implement these files after the coordinator freezes ownership.
Do not change the renderer, APK, fixture media or core to satisfy an observation assumption.

Use ticket63's exact compact real-bot scene and run(capture, tap, observe)/stage_scenario/
assert_scenario interface. Phases are initial, edited and restarted. The ordinary inline callback
uses freshly inspected semantic bounds with a retained screenshot before actual input. Initial and
unchanged restarted launches must be COLD. Incoming static ID1 stays unchanged; ordinary/rich/button
ID1 leaves become ID1109 after the real bot callback edit. Native code must request original
Documents from an initially empty cache; the shared scenario's own bridge requests are excluded
from native request counts through NativeAssetProxy's v4 document journal.

Preserve complete semantic/API assertions from the independent scenario. Retain original phase
PNGs/XML, launch/trace/logcat, phase-local document+asset journals, and actual native destination
names/hash/size before and after unchanged restart. Static original rendering uses the thumbnail
`2_2.jpg`; do not require a static-main GET. Animated original rendering loads main
`-1_1109.webm` plus the shared thumbnail. Do not invent another destination or require every
carrier to start its own transfer. Determine native coalescing from observed original lifecycle.
Restart must preserve original document/file caches, retain displayed content and require no new
asset GET for the unchanged original cache control. Report a contrary original behavior instead
of weakening or manufacturing that expectation.

Visual evidence must establish the original blue diamond thumbnail in each visible initial
carrier, then actual animated colored geometry in ordinary and rich text/button carriers. Retain
a short original Android screen recording or screenshot burst. Use semantically identified message
regions and the separately authored fixture geometry: stationary green marker x8..23/y8..23 and
24-pixel moving square at (10,35), (28,55), (46,35), (64,55), with colors red/cyan/yellow/purple.
Require all four states in cyclic order (duplicate sampled frames and skipped transitions allowed)
at a consistent position/scale; transparent margins and vacated square regions blend with their
original bubble background. A running flag, one frame or a globally changed screenshot hash does
not prove animation/alpha. Original LiteMode/device animation restrictions must be diagnosed and
reported, not bypassed. Match geometry with explicit sampling tolerances for real decoder/scaling
and recording; preserve observed outputs for independent inspection.

Run one serial guest under android-gate with the verified immutable normal24 APK and outer network
guard. Keep unchanged source/APK/profile/probe fingerprints before/after. Retain complete JUnit
including failures; inspect original PNGs and desktop/mobile report previews before declaring
visual acceptance. All scopes still need stronger fault/cancel/unknown/mixed resolver recovery and
wider native regression under ticket58; this lifecycle cannot substitute for those checks.
