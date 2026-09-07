# Verify cleaned rich content through a real bot and original Android

Type: task
Status: ready-for-agent
Work state: resolved after coordinator integration and acceptance
Blocked by: none

Worker owns new tests/test_rich_cleaning_round_trip.py, tests/test_android_rich_cleaning.py,
tests/probes/android_rich_cleaning.py and this ticket. The coordinator owns integration, shared
probes, static-check configuration, docs and all Android execution. Use a separate worktree.

The [cleaning contract](../../../docs/development/rich-text-cleaning.md) is fixed; the Python
implementation on ticket 12 is reviewed and frozen separately. Prepare a small independently
authored dirty-input and canonical-output scene. Reuse the real standard-library HTTP fixture bot,
stage_rich_scenario and rich_round_trip flow, and the existing native probe's scene_checks seam.
Keep setup/expected assertions shared between the simulation and native host tests where useful.
Do not modify shared probes or copy client-derived code into these Python files.

Initial and edited messages must expose the canonicalization difference through complete real Bot
API replies and durable history, then through actual native serialization. Cover accepted tab,
Unicode removals, a direction-marker run, preformatted language and unchanged Persian/ZWNJ text.
Use short visible strings for the original 320 x 640 profile; long truncation boundaries belong
to the core contract tests. Retain raw input separately from expected canonical output. Switch the
edit to RTL and verify the live view and cold restart with original PNG/XML. Expected content
must not be computed using the validator, codec or source input transformation code.

The simulation case should demonstrate missing normalization on this base via the real bot and
complete output. The native case should compare the same complete canonical semantics and retain
normal guest isolation/accounts, launch status, applied-edit trace and report evidence. Reuse the
existing APK: no Java change or build is needed for world-side normalization. No input fallback,
runtime egress, renderer/profile change or new capture API is assigned.

Run focused simulation red and scoped lint/format/mypy under the pinned offline environment and
outer network guard. Positive simulation and native execution depend on the coordinator merging
the frozen core fix; report this honestly rather than weakening expected output. The worker must
not launch guests or build an APK. Commit only owned files and hand back a frozen clean branch;
keep the ticket claimed until coordinator integration and acceptance.


## Worker handoff

The three assigned Python files are implemented. A short independent input/output fixture covers
accepted tabs, removed Unicode characters, adjacent direction markers, preserved Persian/ZWNJ,
preformatted language cleaning and omission, and a table caption that cleans to empty. Raw input
and expected canonical output are separately retained in each run. The simulation asserts complete
real HTTP bot send/edit replies and reopened durable history. Its shared assertions are reused by
the native host test; the new native probe only supplies scene checks to the existing helper.

The native test requires complete serialized message records, initial/live RTL edit/cold-restart
PNG/XML, successful cold launches, applied-edit trace, zero accounts, local-only networking and
emulator filesystem isolation. It generates a report retaining raw/expected content, observations,
timings, APK fingerprint and original screenshots. No shared helper, Java, APK or profile changed.

Verification on the assigned base before ticket 12 integration:

- Offline provisioning and the editable-install path check passed in this checkout.
- The real-bot simulation is red: one failed test in 1.96 seconds. Its subprocess succeeds;
  complete output comparison catches dirty heading/text/language/caption values in bot replies
  and durable history. For example, `Clean\tsta\u202art` remains dirty instead of `Clean start`,
  and edited language `\u202c\u033f` remains present instead of being omitted.
- Scoped Ruff, formatting and strict mypy pass for all three new files. Deliberate Persian
  fixture strings have a local RUF001 exemption; no shared lint configuration changed.
- Positive simulation, Android execution, original screenshot inspection and combined acceptance
  are deferred to the coordinator after integration of the frozen ticket 12 fix. No Android
  tests, builds or full gates ran in this worker.

Reproduce the simulation red on this base in the provisioned shell:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest tests/test_rich_cleaning_round_trip.py'
```

Run Ruff/check-format/mypy against `tests/test_rich_cleaning_round_trip.py`,
`tests/test_android_rich_cleaning.py` and `tests/probes/android_rich_cleaning.py`.
Retained local JUnit, test log, raw/expected/actual JSON and static logs are under the ignored
worker artifact directory identified in the coordinator handoff. All worker commands are terminal.
Coordinator follow-up: add the new files to shared static-check coverage where explicit file lists
are used, integrate ticket 12 before this ticket's positive checks, run the focused native test
with the existing APK, inspect all three original captures and reconcile shared evidence docs.

## Coordinator acceptance

Both frozen worker branches are merged. All 91 World/HTTP tests pass in 24.84 seconds, including
the previously deferred Unicode property. The independent real-bot regression passes in 1.01
seconds after its recorded failure on the old base. The full core gate passes 336 tests in 48.58
seconds with 80.67% coverage and no skips. Repository-wide lint/format, every documented strict
mypy scope, the Nix workflow check, offline package build, installed-wheel list scenario with
complete semantic verification, and installed World normalization verification pass.

The focused original-Android normalization test passes in 65.98 seconds using the existing APK.
It verifies complete native initial/edited serialization, live RTL editing, cold restart, applied
edit trace, successful launches, zero accounts and network/filesystem isolation. All three original
PNG captures were visually reviewed. Raw input, independent expected content, complete actual
observations, PNG/XML and HTML report remain in ignored artifacts. No Java, APK, renderer or
profile change was needed. The preceding full 38-case Android gate predates this correction;
focused native acceptance does not claim a full 39-case rerun. All checks are terminal.

Reproduce the native acceptance in the provisioned Android environment and documented outer
network guard, holding the shared `android-gate` lock, with
`pytest -m android tests/test_android_rich_cleaning.py`. The full core gate selects `-m 'not android' -n 4` with source coverage and its 80% floor in
the guarded pinned environment. Rich actions and the wider product inventory remain open.
