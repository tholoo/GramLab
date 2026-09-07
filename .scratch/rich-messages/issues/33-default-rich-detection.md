# Establish default rich-text enrichment behavior

Type: feature
Status: needs-triage
Work state: source review complete; enrichment contract unresolved
Blocked by: missing server behavior evidence or consultation on a local fidelity policy

The first operational workflow needs omitted `skip_entity_detection`. The
[pinned review](../../../docs/development/rich-auto-detection.md) proves that omitted/false enables
a server autolink flag, but retained open source does not implement the automatic enrichment
rules. Structured URL/email/phone support with explicit skip does not satisfy this requirement.

Preserve the full requirement. Gather independently supplied/public reference observations for
the documented grammar, nesting, block-role and send/edit matrix, or prepare a concrete proposed
local emulation policy for user consultation. Do not substitute ordinary-text entity detection
as proven RichText behavior, contact DCs/use accounts, or widen the fidelity target silently.
Other authorized media, explicit rich content and native acceptance work may continue.
