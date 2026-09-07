# Preserve structured URL, email and phone text in World and Bot API

Type: feature
Status: ready-for-agent
Work state: integrated; focused acceptance passed, combined batch gate pending
Blocked by: none; shared contract frozen

Follow [the contract](../../../docs/development/rich-links-contract.md). Core worker owns only
`src/gramlab/rich_messages.py`, new `tests/test_rich_links.py` and this ticket on
`task/rich-links-core`. Coordinator owns capture/real-bot fixtures, shared docs and full gates;
another worker owns World/polling startup. Do not edit those shared files.

Prove current public World/HTTP rejection before implementing the three exact metadata-bearing
recursive RichText types. Test complete JSON/form sends/edits, cleaned canonical output, no-op
edits, persistence/events/client snapshots, missing/wrong/unknown fields, Unicode/limits,
empty/non-address metadata, nested styles/links and unchanged state after each rejection.
Existing rich-button label restrictions remain. Input/output retains the complete structure;
never flatten a link or fetch/validate its destination over a network.

Run new tests plus existing rich-message/Bot API/cleaning suites in the pinned assigned shell and
outer network guard. Run scoped Ruff/format and source mypy; no guest/build/full gate is assigned.
Use own worktree/branch and commit only owned files. Return red/green evidence and a frozen clean
branch with terminal resources; keep ticket claimed until coordinator integration acceptance.

## Worker evidence

The owned World and HTTP suite now covers recursive URL, email-address and phone-number nodes,
canonical metadata cleaning, exact persistence/events/snapshots, no-op edits, text-to-rich edits,
JSON/form requests, size boundaries and rejection atomicity. The pre-change run had four expected
valid-case failures; the completed owned suite has 12 passes. The selected existing suites have one
expected stale assertion that still classifies URL RichText as unsupported; the coordinator owns
that test update during integration.

Coordinator integration replaces the stale unsupported URL case with an unsupported `text_link`
node. The complete 144-case combined rich-link/startup/polling/API selection passes in
60.27 seconds, including independent real-bot and public capture acceptance. An earlier primary
virtualenv pointed to the polling worker; its 6-failure/100-pass result is retained as invalid
integration evidence. After repairing that install, an import-origin guard rejects wrong-checkout
runs before collection. Scoped Ruff/format/mypy pass. Native and full-core batch gates remain.
