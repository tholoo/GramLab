# Batch fresh World creation without weakening durability

Type: task
Status: ready-for-agent
Work state: resolved
Owner: `world-creation-transactions` worker on `task/world-creation-transactions`

The combined core15 runner-timeout case ended with an empty process record and no descendant
heartbeat. Its one-second whole-run budget includes World initialization. The exact timeout cause
is not established. Separate serial and four-worker measurements found variable startup cost in unmodified
World.create. Host-specific timings and raw samples remain ignored. This is a measured startup cost, not proof
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

## Answer

Fresh creation now enables WAL before starting one explicit writer transaction. That transaction
contains all schema statements, the initial custom-emoji counter, schema version 9 and the bound
configuration row. A configuration binding error therefore rolls back the application schema and
version while retaining the caller-owned directory, empty database and WAL journal mode.

The real SQLite regression first failed against the assigned base because the database retained
schema version 9 after the configuration insert rejected an unsupported bound value. It passes
after the change with version 0 and no application tables, indexes, triggers or views. A separate
success control verifies the complete schema-9 table set, counter/configuration state, WAL mode,
integrity and foreign keys through an independent connection, then exercises user, bot, chat and
message operations through `World` and reopens the result.

Comparable local samples used the same 8-serial/32-four-worker `World.create` operation and removed
all temporary databases after close. Before/after source identities and timing results remain in
ignored `.cache/local-notes/world-create-profile-{before,after}.json`. The same operation and sample
counts were used on both revisions. These measurements have no test threshold and do not
establish the exact cause of core15.

The expanded World/storage/migration check passes 106 cases, and the separately contained public
runner check passes 31 cases with `ResourceWarning` promoted to an error. The unchanged one-second
timeout case passed in 2.503 seconds in this run; its scheduling assumption remains nondeterministic,
so this result does not replace the coordinator-owned readiness/liveness correction. Strict mypy,
Ruff lint and Ruff formatting pass for both owned Python files. Red/green JUnit and runner logs are
retained under ignored `artifacts/world-creation-transactions-{red,green}/`; successful disposable
runtime directories were removed.

Primary integration passes55 creation, migration and public-runner cases, including the corrected
detached-child readiness/liveness timeout test, plus strict Mypy and Ruff. JUnit
world-creation-integrated-01.xml is retained. Combined verification remains.

## Combined acceptance

Core16 passes all 1,126 cases at 88.02% coverage, including the creation and real-runner
controls. Static15 passes 64 documented commands. This resolves atomic initialization and its
regression acceptance; the earlier timeout failure remains retained with its causal limitations.
