# Capture animation bursts without a host transfer between every frame

Type: task
Status: ready-for-agent
Work state: implemented on `task/custom-emoji-guest-burst-capture`; coordinator review pending
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

## Implementation and focused evidence

The edited-stage probe now calls the test-only `guest_screenshot_burst.py` helper. One correctly
quoted `adb shell -T sh -c` session captures all 24 original PNGs with the existing 80 ms delay
following every capture. Each screencap is bracketed by guest `/proc/uptime` reads. The parser
requires the observed two-decimal format and converts the start to its centisecond floor and the
end to the next centisecond, explicitly retaining clock-resolution uncertainty. Host command and
transfer duration do not enter these acquisition bounds.

The session emits a token-bound header, 24 ordered records and a terminal count. Records include
original byte size and SHA-256. A single directory pull follows successful capture and framing;
its exact regular-file inventory, sizes, PNG signatures and hashes must all match before output
publication. Publication creates links without overwriting prior captures. A caught publication
failure removes only links created by that attempt, preserving all transferred originals in the
unique staging directory. This does not claim atomic publication across abrupt process death;
a failed probe or incomplete frame set cannot establish native acceptance. Dedicated guest staging
also remains available for diagnosis until ordinary run teardown.

Bounded slow captures are deliberately retained with their actual conservative intervals. The
existing oracle still rejects acquisition intervals of 500 ms or greater, checks one shared spatial
transform, and requires the same authored temporal phase. No oracle, PNG, fixture, profile, APK or
rendering behavior changed. UI07's original failure and all retained images remain untouched.

Focused verification uses the assigned pinned offline environment and real temporary files:

- `artifacts/custom-emoji-guest-burst-initial.xml`: 25 initial framing/transfer controls pass.
- `artifacts/custom-emoji-guest-burst-publication-red.xml`: the independent mid-publication failure
  control fails because 13 final paths remain. The fix preserves all 24 staged originals and removes
  the newly published prefix on the injected exception.
- `artifacts/custom-emoji-guest-burst-verified.xml` and the final-source
  `artifacts/custom-emoji-guest-burst-final.xml`: all 26 focused controls pass under
  `tools/dev default --offline --command unshare --user --map-root-user --net .venv/bin/pytest -q
  tests/test_guest_screenshot_burst.py`. Three controls execute the actual POSIX shell loop,
  `/proc/uptime`, sleep, `wc` and SHA-256 commands. Only the external screencap result is replaced
  with an existing authored PNG fixture. These checks are not native animation evidence.
- Scoped Ruff lint/format and strict mypy pass for the helper, its tests and the edited probe.

Coordinator integration must stage `guest_screenshot_burst.py` beside `android_custom_emoji.py`
in the native test's existing probe-file copy list. Guest dependencies are `sh`, `mkdir`, shell
`read`/`printf`, `/proc/uptime`, original `screencap`, `toybox wc`, `toybox sha256sum`, fractional
`sleep 0.08`, and directory `adb pull`. No guest, APK build, full gate or archived-artifact mutation
ran for this ticket. Fresh native execution remains required before resolving it.

## Coordinator integration

The native staging list and contributor/CI typing scopes include the new helper. All 58 combined
capture-helper and visual-oracle checks pass in `artifacts/custom-emoji-guest-burst-integrated-02.xml`;
scoped Ruff/format and strict typing pass. Helper tests and native probe typing run separately to
preserve their intentionally different import roots. Fresh original Android execution remains
pending; no earlier failed native JUnit is relabeled.
