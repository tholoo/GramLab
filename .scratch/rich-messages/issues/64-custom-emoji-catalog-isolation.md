# Enforce document request IDs and retain catalog isolation regressions

Type: bug
Status: ready-for-agent
Work state: claimed
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

## Answer

Implemented on `task/custom-emoji-isolation` from base
`37a176a0f6208238f14b7f5c7d067ab1632efdc1`. Document lookup now rejects every non-string ID before
normalization or grant authorization, while registration and message-entity integer support remain
unchanged. The redundant thumbnail projection before bot file-identity admission was removed.

The new public regression suite uses actual v4 HTTP requests and World operations to cover the
confirmed integer-ID defect, boolean/noncanonical/mixed requests, identical whole-batch 404s,
transaction rollback and subsequent logical/asset allocation, chosen-low-ID skipping, shared asset
deduplication, concurrent matching/conflicting registrations, reopen/retry, retained edit grants,
and bot/persona/World capability isolation. It exercises both original static WebP and animated
WebM fixtures through the real validator.

The guarded red is retained as `artifacts/custom-emoji-isolation-red.{log,xml}` with the expected
integer-ID 200 mismatch (1 failed, 6 passed). The final focused green is retained as
`artifacts/custom-emoji-isolation-green-final.{log,xml}` (7 passed), and the related existing
World/API/bridge selection is retained as `artifacts/custom-emoji-isolation-green-related.{log,xml}`
(14 passed). Scoped Ruff lint, format and strict mypy pass with logs under
`artifacts/custom-emoji-isolation-{ruff,format,mypy}.log`. Coordinator integration remains pending,
so the work state stays claimed.
