# Reusable list bot and shared capture/callback scenario

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: none

Worker owns examples/rich_lists/ (new), tests/test_runner_rich_lists.py (new), and this ticket.
Coordinator delegates these paths from the integration ticket and retains production walkers,
native probes, builds, shared docs and combined verification. Follow the pinned list contract.

Provide a portable standard-library HTTP bot and a public Scenario consumer that run in both
simulation-only and headless Android modes. Keep input fixtures independent of canonical expected
output: output-only labels must never be resubmitted. Use concise content that fits the existing
320 x 640 profile, with list-only readable identity so missing native item traversal is observable.
Exercise nested unordered/ordered content, all five ordered label types across send/edit, both
checkbox states, an empty item, mixed Persian/English text, wrapping and RTL edit. Use an actual
inline callback to perform the edit; verify complete callback message content and answer. Capture
before input, after edit and through a second cold reopen through the public capture API. Every
public capture cold-launches the client; the coordinator's separate native probe verifies the live
edit. No production toggle or new API is assigned. The coordinator separately verifies bot-owned
checkbox input cannot mutate.

Host tests must assert full expected canonical histories/captures/events, real Bot API send/edit,
callback correctness, unchanged semantic results across modes, and native evidence/isolation/report
metadata where applicable. Include a native ambiguity rejection case for identical readable list
content with differences only in label/value/checkbox/empty-item metadata, including an offscreen
duplicate. A collapsed-details descendant must not supply native identity. Preserve order of
readable fragments. Expected values must be independently authored, not computed by the validator.

Use existing example/test conventions. Run focused simulation tests and scoped lint/format/mypy
under the documented outer network guard. Do not run guests or build an APK: the coordinator owns
native red/green on the integrated build. Retain meaningful missing-feature red if available;
existing integrated core/list capture support is already implemented, so do not invent a red for
an example-only change. Commit a frozen clean branch; leave ticket claimed until integrated native
acceptance. Report pending native checks explicitly.

## Comments

- Claimed on `task/rich-list-example`. This worker owns only `examples/rich_lists/`,
  `tests/test_runner_rich_lists.py`, and this ticket. Acceptance covers the portable real HTTP bot,
  the shared three-capture callback/edit/reopen scenario, independently authored complete expected
  semantic output, and the native ambiguity rejection fixture. Coordinator-owned native build and
  red/green acceptance remain pending after integration.
- Focused simulation passes under the outer network guard: `1 passed, 2 deselected`. Scoped Ruff
  lint/format and mypy checks also pass. The bot performs real local `sendRichMessage`,
  `editMessageText`, update polling and callback answering; the test compares the complete
  canonical world, history, captures and normalized dynamic callback events against independent
  expectations. No Android guest or APK build was run. Native list traversal red/green, three
  original capture inspections, ambiguity rejection, isolation/report metadata and bot-owned
  checkbox immutability remain coordinator acceptance work, so this ticket stays claimed.
- Review correction: the public capture API force-stops and relaunches the client for every capture.
  The post-edit labels are therefore `after-edit` and `cold-reopen`; neither is live-rendering
  evidence. The coordinator-owned native probe remains the live-edit check. The focused offline
  rerun passes with `1 passed, 2 deselected`; scoped Ruff lint/format and mypy also pass. No guest
  was started.
- Native visual review found the original wrapping text stayed on one line and the pinned renderer
  placed ordered `a`/`A` markers beneath their checkboxes. The updated scene lengthens the wrapping
  text and moves checked/unchecked state to two nested unordered items, preserving clear samples of
  all five ordered label styles. The duplicate flips those nested checkbox states while retaining
  equal readable identity. The coordinator records the renderer quirk; this example does not
  normalize or fix it. The final focused offline rerun passes with `1 passed, 2 deselected`; Ruff
  lint/format and mypy also pass. No native test, guest or build was run.
- Coordinator's two-worker trial completed both native scenarios, but the public host assertion
  incorrectly required the callback to remain unanswered at observation. The documented input
  contract permits the real bot to answer before return. Replaying the retained result reproduced
  that assertion in under a second. Accepting either pending or the exact expected answer makes
  both retained mode results pass; a deliberately incorrect answer remains rejected. Complete
  final events and scenario assertions still require the exact eventual answer. No runtime code
  changed. The final original screenshots show real wrapping, clear a/A/i and I/decimal labels,
  nested checked/unchecked items, and equal RTL content through both cold captures. A corrected
  fresh native pair and the combined gate remain pending.

- The corrected second two-worker trial passes the final public native example and complete
  semantics. The separate direct checkbox case reports a cold-launch timeout in that trial, then
  passes alone with unchanged settings. Parallel scheduling remains unaccepted. The combined
  gate will run serially; final negative-fixture and combined acceptance remain pending.
