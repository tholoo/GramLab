# Public rich-button scenarios

The experimental runner exposes `Scenario.rich_buttons(chat_id=..., message_id=...)` and
`Scenario.tap_rich_button(target_id=...)` for canonical rich-message buttons. The shared contract
covers callback, copy and disabled actions in simulation and headless Android. The integrated
simulation scenario and host boundary checks pass within the 780-test core gate (86.71% coverage).
The new original Android APK builds offline with a verified signature; native acceptance
remains pending. Host tests that substitute guest files do not establish native behavior.

## Observe and select

Within an already configured private scenario component:

```python
observed = scenario.rich_buttons(chat_id=chat_id, message_id=message_id)
selected = next(
    target for target in observed["targets"] if target["path"] == ["blocks", 0, "buttons", 0]
)
receipt = scenario.tap_rich_button(target_id=selected["target_id"])
assert receipt["status"] == "succeeded", receipt
```

An observation contains `chat_id`, `message_id`, `message_revision` and `targets`. Each target has
an opaque `target_id`, canonical `path`, complete `button` and flattened `label`. Select by the
expected path and button; duplicate labels and callback data remain separate occurrences.
Observation includes hidden and offscreen occurrences. A native tap rejects an unavailable target;
there is no automatic scrolling, disclosure expansion or long press.

Observing a nonempty native message opens the chat and establishes its actual client lifetime.
A fresh observation can therefore invalidate earlier targets and abandon an unresolved operation.
The allocation is durable before IDs are returned. Empty observations reserve nothing. Both SDK
methods have a separate 180-second socket timeout by default; the manifest must also allow enough
time for the entire scenario.

## Single-use receipts

The first tap consumes its target even when it rejects before dispatch. Repeating the same ID
returns its retained receipt or polls existing evidence; it never repeats input. Concurrent callers
can see `in_progress`. The receipt contains the operation ID, complete target, `status`, `dispatch`,
`effect`, `reason` and `evidence`.

| Status | Meaning |
| --- | --- |
| `in_progress` | The target is claimed and its first operation is still running |
| `rejected_before_dispatch` | No input was dispatched; the consumed target cannot be retried |
| `succeeded` | The selected action has confirmed effect evidence |
| `uncertain` | Intent or input occurred without a confirmed outcome; do not assume failure |

Callback success retains the exact callback creation snapshot and event sequence, with its initial
`answer` equal to `None`. Later bot answers and edits are separate observations. Copy success retains
the selected text and clipboard before/after values. Disabled success retains an unchanged clipboard
and no World effect. Simulation uses a client-local virtual clipboard; native confirmation requires
the original handler and actual clipboard evidence. Only Android supplies original screenshots.

Edits invalidate the old revision even when time does not advance or content changes back to its
original value. Changing the client persona or restarting the application invalidates its old
lifetime. Terminal success and rejection are immutable. An uncertain native operation may resolve
through read-only evidence while its original lifetime remains available; a known mismatch cannot
be upgraded to success. Starting a new observation may deliberately abandon that late completion.

The run has 64 shared slots for issued rich targets and ordinary interactions. Repeated observations
consume more slots. Allocation is all-or-nothing, and claiming a reserved target consumes no second
slot. No IDs or receipts are evicted. Invalid or foreign IDs reject without revealing another run.

## Lost replies and recovery

The SDK never automatically retries either method. A lost observation reply can leave issued IDs
unknown to the caller; a lost tap reply can leave a completed effect. `ScenarioError.outcome_uncertain`
records that ambiguity. Deliberately repeating a known target ID is safe from duplicate input.

The trusted run retains `rich-button-journal.jsonl`, with durable allocation, claim, intent and
bounded evidence. After the supervisor terminates, the outer runner writes
`rich-button-recovery.json` and links it from `result.json` and `report.html`, even when abrupt process
termination prevented the ordinary supervisor observation. A claim without intent recovers as a
consumed rejection; unconfirmed intent recovers as uncertainty. Recovery never replays input or
restores live IDs. Corruption produces a visible recovery failure and preserves the original journal.

The [implementation contract](rich-button-implementation-contract.md) specifies exact schemas,
closed reason codes and byte limits. The independent
[public scenario](../../tests/rich_targets_scenario.py) and
[contained bot](../../tests/fixtures/rich_targets_bot.py) cover duplicate identities, Persian text,
row/inline placements, stale revisions and repeat behavior. Native execution and wider placement,
clipboard-paste, clipping and restart acceptance remain required.
