# Apply the approved bounded custom-emoji timing oracle

Type: task
Status: ready-for-agent
Work state: resolved
Owner: custom-emoji-timing
Blocked by: none

Implement the approved timing criterion in `tests/custom_emoji_visual.py`, its focused independent
unit tests and `tests/test_android_custom_emoji.py` only where needed. Keep all24 exact authored
pixel/state observations, full-sequence forward quarter-frame order, all-four-state coverage and
three-carrier synchronization. Replace only the full-horizon one-second phase intersection with a
search for a contiguous window containing at least20 captures and spanning at least5 seconds.

Acceptance must add a meaningful synthetic red for the old full-horizon rule, prove rejection of
short, reversed, over-skipping, incomplete-state and phase-incoherent sequences, and pass the full
custom-emoji visual host suite. Replay the retained clean normal30 data at
`artifacts/custom-emoji-normal30-regression-01-work/` from the primary checkout without mutating the
evidence; report the exact passing window. Do not run an Android guest, change capture pacing,
production code, assets, renderer patches, public-runner behavior, transfer/cache/fault assertions
or shared documentation. Commit only owned files and this ticket.

## Implementation handoff

The timing oracle now validates state coverage and forward order over the complete sequence, then
deterministically selects the longest feasible contiguous phase window (earliest on a length tie)
with at least20 captures spanning at least5 seconds. `AnimationTiming` retains the old two-bound
indexing/iteration behavior while also returning inclusive capture indexes, capture times, count
and span. The Android lifecycle assertion still checks all24 authored frames independently for all
three carriers, now compares their complete state sequences explicitly, and records each selected
window in the report.

An independent synthetic case has an empty old full-horizon intersection of
`[50,000,001, 20,000,000]` nanoseconds but a valid22-capture suffix. It failed before the oracle
change and now passes. Focused cases also reject fewer than20 captures,20 captures under5 seconds,
reverse order, a three-quarter-frame jump, incomplete state coverage, changed playback speed and a
forward but phase-incoherent sequence.

The read-only replay of
`artifacts/custom-emoji-normal30-regression-01-work/test_original_custom_emoji_edi0/` in the primary
checkout validated all24 retained PNGs for ordinary, rich and button carriers. All three have the
same state sequence and select inclusive indexes2–23:22 captures from105,740,000,000 through
112,580,000,000 nanoseconds, a6,840,000,000-nanosecond span, with inclusive phase bounds
`[-579,999,999, -540,000,000]` relative to capture2. No Android guest was started.

The complete32-case visual-oracle suite passes. The documented strict mypy scope passes for five
files, Ruff lint/format pass for all three changed files, and `git diff --check` passes. Retained
worker evidence is `artifacts/custom-emoji-timing-red.xml` and
`artifacts/custom-emoji-timing-green-final.xml`. Keep this ticket claimed until coordinator review
and integration; the coordinator owns the final resolved state and shared-document updates.

## Integration

The coordinator reviewed commit `71822f5`, reran the32-case visual suite, strict typing across five
files and Ruff lint/format on the merged tree, and accepted the read-only normal30 replay. Ticket120
and its parent ticket116 are resolved without another guest run.
