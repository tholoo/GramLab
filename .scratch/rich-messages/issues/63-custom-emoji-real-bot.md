# Prove a real bot custom-emoji lifecycle shared with native acceptance

Type: feature
Status: ready-for-agent
Work state: open
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
