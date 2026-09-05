# Testing principles

Tests specify observable behavior and catch realistic regressions. Coverage is a backstop, not
proof that GramLab models Telegram correctly.

## Stable boundaries

- Bot API boundary: send actual HTTP requests and assert complete responses, delivered updates,
  and resulting simulated state. Cover both polling and webhook delivery contracts.
- World boundary: assert valid and rejected transitions, isolation, event ordering, persistence
  and recovery through public operations, not private helper calls.
- Client boundary: verify real Android input/output against the shared world. Pair semantic
  assertions with screenshots for behavior only rendering can establish.
- Compatibility boundary: expected behavior comes from pinned official specifications, licensed
  fixtures, or separately obtained observations—not the same code that produces the result.

## Regression loop

For a bug, demonstrate a failing test at the relevant boundary before fixing it. Confirm the
failure is the reported behavior, make the smallest justified change, then run focused tests
and the applicable full gate. Record red and green evidence.

Compare full structured outputs when they are the contract. Use golden files for substantial
stable renderings and review changes explicitly. A spy saying a method was called is not enough.
Every meaningful positive case should have an applicable rejection, boundary, stale-input,
wrong-identity, retry or interruption case.

## Determinism and concurrency

Inject time and randomness at owned boundaries; preserve seeds and event traces. Use independent
worlds, temporary directories and bot state per run/worker. Test both world isolation and races
inside one world. Reproduce concurrency through controlled scheduling where possible, not sleeps.
Do not claim Android animation timing is deterministic until measured and controlled separately.

Use property-based tests for invariants such as identifier isolation, permission transitions,
entity offsets, byte limits, round trips and replay equivalence. Shrink failures when possible.
Keep real fast collaborators; substitute externally controlled systems at explicit boundaries.

## UI and language

Exercise independent user, chat, client and bot-language preferences, especially Persian/English
mixing, RTL/LTR, نیم‌فاصله, emoji sequences and translation expansion. Specify the font, theme,
density, viewport and animation capture policy for visual evidence. Prefer accessible/semantic
targets, with screenshots and structural inspection where native views expose too little.

Simulation-only results do not prove UI fidelity. A rendered fixture does not prove server
acceptance, a real custom-emoji entitlement or a production document's availability.

## Quality gate

For each changed test, answer: what plausible incorrect implementation would make it fail?
Check that expected values are independent and the test survives behavior-preserving refactors.
Unknown API methods must fail explicitly, never receive invented success.

The first behavioral suite covers the [Linux process boundary](docs/development/runtime-boundary.md).
Run it in the provisioned Nix shell with real namespace support. The manually dispatched CI
requires the suite and coverage gate; unavailable containment must fail visibly. Do not use
`passWithNoTests` equivalents or substitute these tests for Android evidence.
