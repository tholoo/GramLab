# Original rich copy and disabled effects

The opt-in [geometry experiment](../../clients/android/experiments/rich-actions/README.md) has
bounded native evidence for a copy row and a disabled inline button. A real isolated HTTP bot sends
the complete rich message. One ordinary row tap copies the exact synthetic payload; ordinary paste
puts it into Telegram's original composer. After deletion and one disabled-button tap, a second
paste retains the same payload. No message, callback, bot action or World event is created.

## Verified boundary

The original renderer, clipboard implementation and composer are unchanged. The GPL observer adds
only mutually exclusive copy/disabled metadata from original action objects to the previously
accepted callback experiment. Normal APK/source remain separate. The experimental build passes
offline in 2 minutes 32 seconds. Its preceding callback-only APK explicitly refuses the new fixture
before input (102.51 seconds), retaining zero taps and successful absent/wrong activation checks.

The first new-APK run exposes a harness mistake: Android's clipboard overlay covers the composer,
and a redundant focus tap hits the overlay's Share control. Actual XML shows the composer already
focused. Direct ordinary paste then succeeds; another trial identifies an unnecessary Escape key
clearing that focus before the disabled check. Both failures are retained. The corrected harness
requires existing original focus, pastes/deletes through ordinary guest keys, and performs no
synthetic clipboard read or input retry.

The third run satisfies all native assertions and reaches report generation in 98.39 seconds.
It verifies absent activation, fresh wrong-message unavailability, exact native action bytes,
process/nonce/generation and bounded age, two ordinary taps, both exact pastes, both draft clears,
complete World/history/event/pending/API invariance, native callback exclusion and cold restart.
The two final geometry samples are 384 ms and 280 ms old, inside the five-second bound. All
thirteen original images were inspected against the observed rectangles and visible original
controls. Android's transient clipboard overlay remains in the original captures; it is not removed.

That pytest run fails solely because eleven screenshots exceed the existing report limit of
eight. The reporter limit is preserved. The fixture now writes two reports with eight and five
images, including the additional immediate-feedback images. The extracted `validate_and_report`
function rechecks every native assertion against the retained result, then creates both reports
in 0.28 seconds. Hash comparison confirms original PNG/XML/JSON/JSONL evidence is unchanged.
The original failing JUnit is retained; this is native acceptance plus verified postprocessing,
not a claimed uninterrupted passing pytest run. No guest is restarted for the report-only fix.

Both reports pass browser checks at 390×844 and 1280×900: all thirteen original images load, no
horizontal overflow or external resource request occurs, and four browser captures were inspected.
The owned preview/tab are closed. The existing callback experiment passes on the new APK in
101.82 seconds, with all six original captures inspected. Scoped simulation, lint/format/strict
typing and the updated offline workflow check pass. The normal 41-case resumed inventory and
preceding 390-test core gate remain separate evidence.

## Reproduce and remaining scope

The [ticket](../../.scratch/rich-messages/issues/21-rich-copy-disabled-native-experiment.md) records
explicit simulation/native commands. Native execution selects a separately fingerprinted APK via
`GRAMLAB_RICH_ACTION_EXPERIMENT_APK` and
`tests/rich_action_effect_experiment.py::test_experimental_original_copy_and_disabled_effects`.
The test filename remains outside default discovery. Local fingerprints, original failed runs,
retained validation and reports stay in ignored artifacts.

This proves a short LTR copy row and disabled inline control. Other placements, RTL/nesting,
duplicate/stale edits, long-press, atomic observation/touch and public targeting remain unaccepted.
Simulation verifies canonical shared content and state without inventing a clipboard. No asset,
media, custom-emoji or Mini-App support follows from this experiment.
