# Capture animation bursts without a host transfer between every frame

Type: task
Status: ready-for-agent
Work state: open
Blocked by: coordinator integration and fresh native acceptance

Own this ticket, the burst capture portion of `tests/probes/android_custom_emoji.py`, a small
test-only capture helper under `tests/probes/` if needed, and focused capture-helper tests.
Coordinator owns the animation oracle, native execution and shared documentation. No APK,
renderer, fixture, profile or product-runtime changes.

Fresh UI07 completes the actual lifecycle but rejects one screenshot acquisition interval of
500.3 ms. Each of the 24 samples currently waits for separate host screencap and pull commands.
Batch the original guest screencaps and retain per-frame monotonic acquisition bounds in the
guest, then transfer the completed burst together. This should reduce host round trips and
avoid including file-transfer latency in the capture interval. Preserve original PNG bytes,
24 ordered frames and the explicit capture delay; do not fabricate timing or retry a favorable
subset. Keep the authored animation period and existing spatial/timing acceptance unchanged.

Use a monotonic guest clock and explicitly conservative bounds for its measured resolution.
Validate framing, exact frame count, ordered bounded timestamps and command failures. Quote
the actual ADB shell boundary correctly. Keep files in the dedicated guest/test staging area;
do not touch any other runtime. The helper may execute ordinary screencap/file transfer only.
Focused tests should exercise the real host shell/record parser with independently supplied
command outputs, including malformed, incomplete and failed captures. They are not native
animation evidence. Preserve UI07's failed JUnit and all retained images. No guest, build or
full gate is assigned; return a clean frozen branch and exact focused evidence.
