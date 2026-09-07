# Prove explicit mentions through real bot and original Android

Type: feature
Status: ready-for-agent
Work state: open
Blocked by: 52 for native execution only

Own this ticket and new files `tests/fixtures/rich_mentions_bot.py`,
`tests/probes/rich_mentions_round_trip.py`, `tests/probes/android_rich_mentions.py`,
`tests/test_rich_mentions_round_trip.py` and `tests/test_android_rich_mentions.py`.
Coordinator owns shared docs, existing media probes, patch series, source, APK and all guest runs.
Follow the frozen mentions contract, approved proposal and existing contained real-bot/native
rich-link scenario conventions. Do not edit core/SDK, existing broad fixtures or dependency files.

Use a real contained polling bot with JSON/form Bot API and a shared SQLite World. Admit two
third-party contacts to that bot while keeping them outside the observing recipient's other
conversations. Start with a rich mention of contact A using independently specified recursive
Persian/English formatting. An original ordinary inline callback makes the bot answer and edit
to contact B, proving first live disclosure of B. A second original callback removes mentions.
Preserve callback frozen message/User projection, exact message/edit revisions and semantic
history/events/updates/API outcomes. Test canonical output-to-input behavior through public bot
operations. Compare complete independently specified bodies, not copies of production outputs.

Simulation-only and Android use the same bot transitions and expected semantic content. Native
checks use actual original renderer, accessible ordinary inline buttons, fresh current structure
and screenshot before input. Record initial A, live B, removed and cold-restarted states, World
snapshot dependencies at each stage and original native trace. Confirm A disappears from later
snapshot envelopes after removal, B appears before dependent live message application, and final
restart agrees with current World state. Do not open mention profiles or external destinations.
The dedicated guest must retain account/network/filesystem isolation and fresh owned state.

Use existing public reporting with at most four primary captures and explicit limitations.
This proves structured explicit mentions only; automatic detection, mention navigation, custom
emoji, rich-button target APIs and Mini Apps remain separate needs. Do not reinterpret their
absence as operational milestone completion.

Run contained real-bot behavioral tests under the outer loopback guard using this checkout's
verified pinned environment, plus scoped Ruff/format/mypy and native fixture collection.
Coordinator runs native acceptance on the reviewed normal APK under android-gate. No worker APK
or guest. Send frozen clean commit, exact red/green semantic evidence, public comparison coverage,
source files needed for staging and remaining native assumptions. Keep claimed until integrated
real-bot and native acceptance pass; retain ignored artifacts and stop task-owned processes.
