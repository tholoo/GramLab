# Reduce repeated handoff reading and accidental serial core gates

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

Coordinator owns CONTRIBUTING.md, the current handoff and its historical archive. No runtime,
test selection defaults, CI policy, product scope or approval boundary changes are assigned.

The always-read handoff has grown to 7,302 words of repeated checkpoints and superseded next
actions. Keep current decisions, pending consultation, exact verification caveats, remaining goal
and workflow in the entry document. Preserve the old contents exactly in a linked historical
archive beside it so relative source/evidence links retain their meaning. Review the compact
entry against the archive; ensure current blockers and failure qualifiers survive.

CONTRIBUTING's broad serial pytest example conflicts with the already established guarded
four-worker non-Android development recipe. Clarify that recipe and keep guest checks separately
locked/serial. Retained evidence matches all 390 passing core identities: prior parallel 54.01
seconds, later serial 195.36 seconds plus 41 unavailable Android skips. These are development
observations, not a controlled performance benchmark. The exact worker count of that latest
parallel log is not recorded; four workers are explicitly documented in earlier accepted gates.

Validate archive preservation, all local Markdown links, shell syntax of the adjusted command,
diff scope and public-tree privacy. A documentation-only correction does not require another
core or guest run. Mark resolved after these checks and review; record exact local evidence
outside tracked files.

## Resolution

Current handoff reading falls from 7,302 to 998 words; the old text is preserved exactly after
a historical preface in the linked archive. Independent review confirms the full goal, pending
photo consultation, failure qualifications, unsupported surfaces and earlier-work pointers
survive. All 138 local Markdown documents pass the maintained link/configuration validation;
the changed recipe parses as Bash, archive preservation and diff/privacy checks pass. The core
recipe now explicitly selects non-Android tests with four workers inside the required guard;
Android and CI scheduling policies are unchanged. No runtime test was rerun for these docs.
