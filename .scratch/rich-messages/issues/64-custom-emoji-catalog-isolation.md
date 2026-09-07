# Enforce document request IDs and retain catalog isolation regressions

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: none

Own this ticket, `src/gramlab/world.py` only for the strict document-ID admission correction and
redundant thumbnail calculation cleanup, plus new `tests/test_custom_emoji_isolation.py`.
All existing tests, other production modules, native code and shared docs remain coordinator-owned.

An independent isolated request has shown `/v4/custom-emoji-documents` accepts integer IDs: JSON
`{"custom_emoji_ids":[7]}` returns the granted document with status 200. The frozen contract requires
1–200 canonical positive signed-64 decimal strings exactly. Add actual HTTP red/green coverage for
integer/bool/noncanonical/mixed malformed lists, then enforce the boundary before normalization or
authorization so malformed requests return 400; well-formed unknown/ungranted/mixed requests retain
the identical 404 without partial results. Do not narrow World registration/entity integer IDs.

Retain independent public behavioral regressions required by ticket59: conflicting request/ID
registration rollback (including subsequent allocated logical and asset IDs), chosen-low-ID
allocator skip, identical main/thumbnail deduplication, concurrent same/conflicting registrations,
reopen and retry, retained old/new grants after edits, two bots/personas/Worlds and cross-bot/world
file capabilities. Prior read-only probes passed these cases; make expectations literal and
observable through public methods/actual HTTP. Use real original static/animated fixtures and real
decoder where relevant. Avoid copying expected results out of the implementation or private SQL.

Run only focused tests in the outer loopback-only guard with unique retained red/green JUnit/logs,
plus scoped Ruff/format/strict mypy. No full gate, build or guest. Follow AGENTS/handoff/TESTING and
parallel workflow, claim/check assigned worktree, use its pinned environment and imports, commit
only owned files and return frozen clean tip with all processes terminal.
