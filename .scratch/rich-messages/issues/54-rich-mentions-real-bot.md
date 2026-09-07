# Prove explicit mentions through real bot and original Android

Type: feature
Status: ready-for-agent
Work state: resolved by rich-mentions-real-bot worker
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

## Worker handoff: contained semantic gate passed, native execution pending

Task `rich-mentions-real-bot`, branch `task/rich-mentions-real-bot`, assigned base
`fa7869b41a9acb304f97541b726a4dafbc84ba50`. Only this ticket and the five assigned new files change.
The prior native branch remains frozen. No core/SDK/public schema/source/APK or shared docs changed.

`rich_mentions_bot.py` is an independent HTTP consumer, with no simulator import. It sends
recursive bilingual mention A with forged caller profile fields using JSON, then performs a
canonical no-op by feeding the returned full User object through form input. It polls two actual
callback updates, answers each, edits first to B using form input and then to unmentioned content
using JSON, verifies a returned-output no-op at every phase, and drains each update. The real bot
uses only its private component filesystem and the explicitly configured local endpoint.

The shared scenario creates Sara (1), Echo (2), Arman (3) and Mina (4). Only the bot has private
conversations with both contacts; the observing persona has only chat 1. Bot stdin gates *polling*
at each phase, not the edit itself: each edit is driven by the delivered original-button callback.
This makes the frozen, unanswered callback receipt independently observable before the bot runs.
Host mode uses the real v3 callback endpoint; native mode substitutes original Android input only.

The full independent oracle covers 13 complete Bot API status/body records, returned full User
profiles, all three no-op errors, three delivered updates, all 17 World events, final history and
empty pending queue, four snapshots, six frozen callback receipts, full and truncated historical
change envelopes, and both other personas' complete snapshots. Snapshot users are [1,2,3] initially,
[1,2,4] after the live edit, and [1,2] after removal/restart; replay still supplies the identities
from the selected older bodies. Rich-message revisions are 9, 13 and 17; the user request remains
revision 8. No-op operations consume no events, message IDs or revisions. Expected content is
specified in the test module independently of the bot and production serializers.

Native probe assumptions and scope:

- Uses the coordinator's normal APK with patch 0022 and optional `BridgeProbe ... mentions` mode.
- Four primary PNG/XML pairs and report captures: `initial`, `edited`, `removed`, `restarted`.
  Before each input it refreshes the corresponding phase's screenshot/structure, replacing that
  same primary filename, then chooses the smallest matching original inline-button bounds.
- Requires the established AOSP viewport 320 x 640 at 160 dpi, original accessible ordinary inline
  labels and no scrolling for this bounded scene. No mention label/profile/destination is tapped.
- Initial native snapshot excludes B. B and removal must appear in the original live UI with
  `events_applied` trace evidence. Separate `app_process` TL codec observations run only *after*
  each live capture, so they cannot prime the application's controller user cache beforehand.
- Complete native codec/user/history-user values, two cold launches, four UI scenes, two real
  input targets, no bridge/startup/event failures and existing guest isolation are asserted.
  Cold restart force-stops the application and relaunches the same durable World configuration.
- Controller dependency ordering still requires the coordinator's source review and native
  envelope gate; this probe does not invent an observer or claim to inspect private cache timing.
  Automatic detection, navigation, custom emoji, rich-button target APIs and Mini Apps remain
  explicit limitations in the public report, not completed milestone features.

Verification in the assigned checkout:

- `tools/worktree check rich-mentions-real-bot` passes; assigned base is an ancestor of HEAD.
- Provisioned using this checkout's `tools/dev default --command uv sync --locked`; verified
  `uv run --locked python` imports `gramlab` from this worktree.
- Guarded current-core gate: `tools/dev default --command bash -c` wrapping
  `unshare --user --map-root-user --net bash -eu`, `ip link set lo up`, then
  `.venv/bin/pytest tests/test_rich_mentions_round_trip.py --basetemp=artifacts/mentions-real-bot-02 --junitxml=artifacts/mentions-real-bot-02.xml`:
  **1 passed in 1.67 seconds**. Complete retained evidence lives beneath
  `artifacts/mentions-real-bot-02/test_real_bot_mentions_disclos0/`, including the result,
  private bot's 13 API records and World database.
- Meaningful historical red: an ignored `git archive` export of pre-mention core commit
  `4f21e06a0bc729c2567ffb9612561b8e7f5811ad` replaced only the *contained run's staged* `gramlab`
  directory. The exact same new bot/scenario ran under the same outer guard and runtime profile.
  It received the ordinary update, then `sendRichMessage` rejected with HTTP 400 and
  `GRAMLAB_UNSUPPORTED: rich content fields`; the scenario exited 1. Evidence is retained in
  `artifacts/mentions-real-bot-baseline/{baseline-evidence.json,stderr.log,bot/api.jsonl}`.
  Historical source is private `.cache/mentions-baseline-source`; current source/imports were
  never replaced. Reproduce by staging the five scenario files normally and substituting only
  the contained run's core directory with that commit's `src/gramlab` before `Sandbox.supervise`.
- The first test attempt had a missing artifact parent directory during pytest setup. Its JUnit
  remains `artifacts/mentions-real-bot-first.xml`; it is not counted as behavioral red.
- Scoped `ruff check`, `ruff format --check` and `mypy` pass for all five new Python files through
  `tools/dev default --command uv run --locked`. Native `pytest --collect-only` collects one test;
  no native test, guest or APK build was run. `git diff --check` passes.

Coordinator staging: use `stage_scenario` from `test_rich_mentions_round_trip.py`; it copies
`rich_mentions_bot.py`, `rich_mentions_round_trip.py` and existing `component_bot.py`, the current
core package and component profile. Native staging additionally requires existing
`emulator_process.py`, `android_guest.py`, new `android_rich_mentions.py`, the reviewed APK and
emulator profile. The new native test performs that staging without altering shared files.

Coordinator must integrate, independently review the native assumptions, run the new original
Android test under android-gate with the reviewed normal APK, inspect the four images and report,
and update shared compatibility/handoff/CONTRIBUTING evidence. The native test's outcome is not
claimed here. Keep this ticket claimed until native acceptance passes. All worker-owned processes
and scoped Sandbox components have exited; no build/guest/resource locks were taken. Branch is
clean and frozen at handoff, with ignored diagnostic artifacts retained.


## Integrated acceptance

Coordinator review and the integrated contained real-bot test pass. On normal23, the original
Android test passes in 102.02 seconds: initial A, two real inline taps, first live B disclosure,
mention removal and COLD restart agree with the complete semantic/API/native expectations.
All four original captures and desktop/mobile HTML previews were inspected; all images load,
there is no horizontal overflow and the self-contained report fetches no subresources. The
preview's owned tab/server are closed. Capability/account/network/filesystem checks pass.
The combined non-Android suite passes 498 tests at 81.98% coverage in 69.17 seconds, with full
Ruff check/format and scoped mypy passing. The same normal23 native batch also passes all four
photo faults/recoveries; all eight images are inspected. The original JUnit has two passing tests,
no failures or skips, and verifies unchanged sources/APK. Ignored artifacts live under
`artifacts/mentions-ui-and-photo-faults-01/` and `artifacts/mentions-and-media-core-full-02.*`.
Broader native regression, automatic detection and other approved rich/media features remain
separate requirements; this resolution covers the assigned explicit mention real-bot workflow.
