# Pin ordinary Bot API HTML formatting behavior

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: none for research

Research worker owns this ticket and `docs/development/html-formatting-references.md` only,
on `task/html-formatting-contract` in its assigned separate checkout. Follow the parallel
workflow, research skill, licensing and upstream guidance. Coordinator owns implementation,
shared docs and architectural decisions. No runtime launch, dependency change or source import.

Investigate ordinary `sendMessage` and `editMessageText` HTML parse mode against the pinned
official Bot API server and TDLib revisions used by the existing rich-photo research. Record
case handling, interaction with explicit entities, supported tags and attributes, escaping,
malformed input, nested formatting, pre/code language, blockquotes, UTF-16 offsets, cleaning,
message limits and generated entities. Distinguish parser output from later normalization and
validation; cite immutable primary-source lines and label moving documentation. Identify
documented boundaries that cannot fit GramLab's existing nine formatting entity types without
further work. Do not silently prescribe a reduced fidelity target or copy implementation.

Produce one concise findings document with independently derived input/output examples suitable
for public HTTP tests, important rejection cases, and clear unresolved questions. Inspect local
acquired sources first; external reference research only if needed, never account/DC calls.
Validate links and changed-tree privacy, commit owned files, and return a frozen clean branch
with exact evidence and terminal resource state. Research is not implementation acceptance.

## Answer

Pinned findings, independently derived parser fixtures, incompatibilities with the current nine
entity types, and unresolved whole-message tests are recorded in
[the HTML formatting source contract](../../../docs/development/html-formatting-references.md).
The key integration boundary is that HTML parser output can contain unsupported types and
overlaps which TDLib repairs only during its later send-time normalization; it cannot safely be
passed straight to GramLab's existing entity validator.
