# Freeze the approved rich-button implementation contract

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: no new user approval; implementation workers wait for the shared contract

Coordinator owns the shared contract, task split, handoff and compatibility records. Translate
the approved rich-button proposal and ADR 0005 into exact SDK/control identities, receipts,
transaction boundaries and GPL observation/correlation fields before assigning implementation.
Keep current v4 message schemas strict and preserve original native input and drawing.

Independent read-only agents review simulation recovery and native request correlation while
the coordinator specifies the joint contract. The native source review establishes that a
separate app-private observation schema can carry existing v4 revisions and actual callback
request/response identities; allocating a new semantic bridge version is unnecessary.

Acceptance: one portable contract with exact field ownership, canonical occurrence ordering,
single-use and uncertain outcomes, bounded records, client lifetime/clipboard rules, native
freshness and correlation, plus independent worker scopes and observable acceptance gates.
Do not treat a contract review as runtime or fidelity evidence. Native emoji acceptance and
current host regression integration continue independently.
