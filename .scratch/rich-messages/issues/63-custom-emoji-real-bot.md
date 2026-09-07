# Prove a real bot custom-emoji lifecycle shared with native acceptance

Type: feature
Status: ready-for-agent
Work state: contained semantic implementation integrated; native acceptance pending coordinator
Blocked by: none for contained semantic implementation; native rendering is coordinator-owned

Own this ticket and new `tests/fixtures/custom_emoji_bot.py`,
`tests/probes/custom_emoji_round_trip.py`, `tests/test_custom_emoji_round_trip.py`.
Do not change production, native patches/probes, media fixtures or shared docs. Use the frozen
custom-emoji implementation contract and the existing mention/media contained-bot harness pattern.

Provide `run(capture=None, tap=None, observe=None)` plus exported host `stage_scenario` and
`assert_scenario` helpers like the mention lifecycle, with phases initial, edited, restarted.
Capture receives phase and the authorized v4 configuration; tap receives previous phase and exact
ordinary inline keyboard label. Capture hooks own opening/live update/unchanged COLD restart.
Observe may add private native observations under client; never include capabilities in results.

Freeze this compact scene for the native successor: user Sara (ID 1, fa), bot Echo (ID 2,
gramlab_echo_bot), second uninvolved persona ID 3; one private chat user1/bot2. Register static
logical ID1 from emoji-static.webp + emoji-thumbnail.webp, and animated logical ID1109 from
emoji-animated.webm + the same thumbnail; both free true and needs_repainting false. Assets are
static main1, thumbnail2, animated main3. Incoming message ID1 is `سلام 👩‍💻`, custom emoji
entity offset5 length5 ID1. The contained bot imports no simulator code. It consumes this update,
looks up/deduplicates/sorts both Sticker descriptors, downloads exact scoped main/thumb bytes,
and sends ordinary message ID2 `Ordinary 👩‍💻` (offset9 length5 ID1) with inline keyboard label
`Animate / متحرک` and data `emoji:animate`. It also sends rich message ID3: paragraph `Rich `
plus ID1 custom-emoji leaf with alternative `different`, then a button row whose disabled button
label is `Badge ` plus ID1 leaf with empty alternative. Use skip_entity_detection true explicitly.
Keep the scene short; do not add headings/extra visible messages.

One callback on ordinary message ID2 causes real bot answer then edits both bot messages to
ID1109, preserving text/alternatives and removing the ordinary keyboard. Incoming ID1 remains
unchanged as a static control. Include a same-content edit rejection. Retain full independent
expected API results/updates, history/events, all three v4 snapshots, selected live changes and
frozen callback responses before/after edit/reopen. Check old/new retained grants, ungranted/mixed
lookup rejection and the uninvolved persona's empty catalog/assets. Dynamic world/callback/file
capabilities may be validated structurally and correlated; do not derive the expected contract
from production helpers or use screenshot/hash changes as rendering proof.

Run focused contained semantic test(s) in the outer loopback-only guard, scoped Ruff/format/strict
mypy, retaining unique JUnit/logs. No build or guest. Frozen complete handoff includes hooks and
portable reproduction so the coordinator can add actual rendering, animation, request and cache
oracles separately. Claim/check assigned worktree, commit only owned files, keep branch frozen.

## Worker handoff: contained semantic lifecycle passed

Task `custom-emoji-real-bot`, branch `task/custom-emoji-real-bot`, assigned base
`6340a2d22fc589b99ee916726f775e7e5b2b5999`. Only this ticket and the three assigned new Python
files change. No production, native, media-fixture, lock or shared-document file is committed.

`custom_emoji_bot.py` is a contained stdlib HTTP consumer with no simulator import or access to
the authoritative World. It consumes the exact incoming update; requests IDs 1109, 1 and 1109;
checks the deduplicated numeric order; downloads both main files and the shared thumbnail through
the bot-scoped `getFile` identities; compares all four responses byte-for-byte with its private
copies; and publishes only ordinary message 2 and rich message 3. It verifies a same-content rich
edit rejection, then polls the one original ordinary-button callback, answers it, edits both
messages to animated ID 1109 and drains its update queue.

The shared probe registers actual static WebP and VP9 WebM bytes through World, starts the real
Bot API server and contained bot, and exposes the frozen native hooks. `run(capture=None,
tap=None, observe=None)` calls capture at `initial`, `edited` and `restarted` with the authorized
v4 configuration. It calls `tap("initial", "Animate / متحرک")` once when supplied; otherwise it
publishes the equivalent v4 callback. Observe runs after services reopen and may add private
native evidence under `client`. The final capability scan covers both client personas and the bot.
Host consumers import `stage_scenario(directory, core)` and `assert_scenario(observed)` from
`test_custom_emoji_round_trip.py`.

The independent oracle compares the complete result outside optional `client` evidence. It covers
14 full Bot API status/body records, both complete Sticker projections, correlated dynamic file
identities and exact file paths, four byte downloads, the no-op rejection, two delivered updates,
all 12 World events, final history, empty pending updates, all three complete v4 snapshots, two
selected change envelopes, and the frozen callback before answer, after both edits and after
reopen. It also checks retained old/new grants, initial ungranted and mixed rejection, canonical
string-only document input, all three authenticated v4 asset downloads before and after reopen,
and the uninvolved persona's complete empty snapshot. Expected messages, assets, descriptors,
events and envelopes are literals derived only from the frozen scene and fixture bytes; no
production serializer or screenshot hash supplies expected content.

Verification used this checkout's pinned media environment, whose Python import resolved to this
worktree. The final semantic command was `tools/dev media --offline --command unshare --user
--map-root-user --net bash -eu -o pipefail -c 'ip link set lo up; env PYTHONPATH=tests/probes
.venv/bin/pytest tests/test_custom_emoji_round_trip.py -q
--junitxml=artifacts/custom-emoji-real-bot.xml
--basetemp=/tmp/gramlab-custom-emoji-real-bot-final-green'`: **1 passed in 7.64 seconds**. JUnit and
the terminal log remain ignored under `artifacts/custom-emoji-real-bot.{xml,log}`; the supervised
result, bot stderr, private API log and World remain in the named basetemp directory. Scoped Ruff
check, Ruff format check and strict mypy pass for all three Python files; `git diff --check` passes.

The initial red collected the new test before its fixture/probe existed and failed on the missing
`custom_emoji_round_trip` module. Once implemented, the complete oracle on assigned-base bytes
failed because integer document ID `1` returned HTTP 200 instead of the required canonical-string
HTTP 400. Coordinator commit `8e076158b9a38da682d814780ac3f2bb747ab68d` fixes that separately.
For final worker verification only, the coordinator SHA-guarded exact fixed `world.py` bytes
(blob `6f711593d2b886dd852c976b17c58a1816377563`) and restores the assigned-base bytes before this
worker commit; the production file is neither staged nor committed here.

The coordinator still owns original-client rendering, animation, native request/cache evidence,
and integrated verification. Native staging needs this test module, both new probe/fixture files,
existing `component_bot.py`, the three existing custom-emoji media fixtures, current integrated
core and a reviewed v4-capable APK/profile. The native hook owns opening the initial scene, applying
the one live callback edit and proving an unchanged cold restart. Simulation verifies structured
content and exact bytes; it does not prove original rendering or playback. No build or guest was
run, and all worker-started processes are terminal.

## Coordinator integration

Frozen worker commit `e0fb984c0230c28f579c58b88dbf2dd47f3a934f` is integrated. The complete
contained semantic oracle passes against the actual merged catalog isolation fix. The combined
core gate passes all 615 tests at 82.94% coverage in 85.45 seconds. A preceding gate retained
one large-report timeout during concurrent guest work; the unchanged isolated case passes in
3.09 seconds. This does not establish the cause or erase that failure. Native ticket65 remains
open: four static glyphs are visible in the diagnostic capture, but the readiness assertion
incorrectly requires an accessibility label absent from the original rich button. No live edit,
animation or restart acceptance follows from that diagnostic.
