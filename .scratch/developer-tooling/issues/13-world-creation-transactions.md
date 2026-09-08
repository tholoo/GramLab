# Batch fresh World creation without weakening durability

Type: task
Status: ready-for-agent
Work state: unassigned

The combined core15 runner-timeout case ended with an empty process record and no descendant
heartbeat. Its one-second whole-run budget includes World initialization. The exact timeout cause
is not established. Separate measurements of unmodified World.create found a2.94-second outlier
among eight serial creations, with111ms median;32 creations on four workers had197ms median.
Host-specific samples and source hashes remain ignored. This is a measured startup cost, not proof
that storage caused that particular test failure.

Fresh World.create enables WAL, then executes its schema without an explicit transaction, so
table creation statements commit separately before configuration is inserted. Investigate and
implement one atomic fresh initialization transaction spanning schema, initial counter, version
and configuration. Keep WAL setup outside that transaction where SQLite requires it. Preserve the
existing durability settings, locking, fresh-directory ownership, returned state and all migration
paths. Do not change run deadlines, mark an unstarted child as cleaned up, or skip failing checks.

Own this ticket, World.create only within `src/gramlab/world.py`, and new
`tests/test_world_creation.py`. No runner/test_runner/shared-doc/lockfile/dependency changes. Work
on an isolated branch; coordinator owns integration and combined verification.

Before editing, retain a public-boundary failed-initialization red: a late configuration insertion
failure must not leave a published schema/version or partial semantic state. Exercise the real
SQLite connection rather than replacing the database or checking for a literal BEGIN string.
Successful creation must retain complete initial state/schema9, support independent subsequent
connections, normal bot/chat/message operations and reopening. Preserve existing migration tests.
This change may leave an owned empty database/directory after failure; do not delete caller data or
pretend a failed initialization produced a usable World.

Measure before/after with the same original World creation operation and comparable serial/four-
worker fixtures. Retain raw samples, source identity and limitations; no timing threshold in unit
tests and no machine details in tracked files. Clean temporary measurement databases immediately.
Use the assigned offline environment and pinned inputs. Run focused World/bootstrap/migration and
runner tests, strict typing and Ruff; no guest/build/network/full gate. Report whether the existing
one-second runner acceptance still fails rather than claiming the optimization proves descendant
cleanup. Freeze the exact branch tip with evidence and terminal processes for coordinator review.
