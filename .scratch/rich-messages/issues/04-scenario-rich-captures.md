# Rich content in public scenario captures

Type: task
Status: ready-for-agent
Work state: unclaimed
Blocked by: none

## Ownership and shared contract

Worker owns src/gramlab/_captures.py, tests/test_runner_rich_capture.py (new), and this ticket.
Coordinator owns examples/rich/, tests/test_runner_rich_example.py, Android integration and shared docs.
No world/API/native rendering changes are required by this ticket.

`Scenario.capture_chat(contains=...)` must recognize content in authoritative rich messages.
Match within one textual fragment: concatenate RichText strings/arrays/wrappers within a text
field; keep different blocks, table cells, captions and credits separate. Traverse nested quote
and details blocks, including details summary and body. Include text content only, never type,
language, alignment or other metadata. Existing ordinary-message substring behavior remains.
These are semantic assertions; Android independently requires actual accessible visible text.
Collapsed/off-screen content can satisfy a simulation assertion but cannot bypass that UI check.
Preserve the original structured history; do not replace rich content with extracted text.

## Acceptance and verification

- Establish the current rejection with a real public runner/scenario request before fixing it.
- Show accepted wrapper-spanning bilingual text, nested block/summary/body text, captions/credits
  and table cells while preserving complete structured capture history.
- Reject absent text, metadata-only matches, cross-block/cross-cell artificial concatenations,
  and another chat's rich text without modifying previous evidence.
- Existing capture, public scenario and rich-message tests remain applicable; run focused checks
  inside the documented outer network guard. No Android build or guest for the worker.
- Keep this ticket claimed until coordinator integrated checks pass. Report red/green evidence,
  exact commit, owned files and open limitations according to the parallel workflow.
