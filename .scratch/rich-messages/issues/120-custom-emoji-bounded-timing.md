# Apply the approved bounded custom-emoji timing oracle

Type: task
Status: ready-for-agent
Work state: claimed
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
