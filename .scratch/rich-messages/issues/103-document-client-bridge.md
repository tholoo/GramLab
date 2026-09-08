# Deliver ordinary documents through authenticated version-5 client HTTP

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

World99 is integrated. Implement only the client HTTP slice from
[ticket102](102-ordinary-document-http-delivery.md) and the
[frozen document contract](../../../docs/development/documents-implementation-contract.md).
Root implements Bot API in a separate branch; native codec101 proceeds independently.

Own this ticket, `src/gramlab/client_bridge.py`, and new `tests/test_document_bridge.py` only.
Do not edit World, Bot API, native patches, existing tests, shared docs, locks or dependencies.
Coordinator owns integration and all shared contributor/compatibility updates.

Expose explicit v5 snapshot/change/callback/send routes, and the corresponding retained image and
custom-emoji routes. Add authenticated GET /v5/documents/ID with exact original bytes. Responses
retain v4 shapes plus the contracted document dependencies and schema5. Preserve old route outputs;
legacy responses selecting documents reject before callback mutation or cursor advance. Use the
integrated World methods and frozen callback dependencies; do not duplicate semantic state.

Retain one-capability authentication, loopback confinement, strict query/header/body/Range
handling, exact Content-Length, no-store, no redirects and closed HTTP connections. Invalid ID
syntax rejects; unknown/ungranted document IDs return identical schema5 HTTP404 document_unavailable
/ Document is unavailable. World.granted_document currently raises ValueError for both unavailable
and invalid IDs: distinguish syntax before translating unavailable lookup errors. Empty semantic
MIME uses application/octet-stream only for the binary response header. Presentation filenames
must never become host paths or request routes. v5 image/custom-emoji failures use schema5.

Follow TESTING.md and offline safety. Drive real contained HTTP requests against real Worlds.
Compare complete snapshot/change/callback/send responses, including users/assets/custom_emoji/
documents/revisions and original frozen retry data after later activity. Use actual ordinary files,
photo/emoji coexistence, numeric IDs2/10/full63bit, cross-persona/World capability denial, unavailable
and malformed IDs, header/query/Range/POST framing rejection, persistence and legacy nonmutation.
Include GET and POST callback forms. Preserve old image/emoji routes through focused regressions.
Do not derive expected responses by calling the same World projection that the handler calls.

Run focused document bridge, existing client/media/custom-emoji/mention bridge, callback and World
checks with ResourceWarning treated as an error, scoped strict mypy and Ruff. No guest/build,
full gate, network, dependency change or upstream source export. Reuse cached packages with a
separate writable environment; retain it through coordinator review to avoid reprovisioning.
Record actual red/green HTTP evidence and limitations, keep runtime data bounded, freeze a clean
actual Git hash and report terminal processes. World-only or native codec evidence cannot replace
this HTTP acceptance; HTTP success does not establish Android rendering/loading.

## Implementation

The authenticated bridge now exposes explicit v5 snapshot, changes, callback POST/GET, client-send,
asset and custom-emoji-document routes. JSON responses retain the existing v4 dependency fields and
add exact World-provided `documents` data under schema 5. Callback creation, lookup and retry use the
World's frozen message/revision dependency boundary; legacy callback routes reject document-bearing
messages before mutation.

`GET /v5/documents/ID` validates canonical positive signed-64-bit decimal syntax before lookup and
uses the existing persona grant. Unknown, ungranted and cross-persona documents share one schema-5
404 response. Successful downloads return exact stored bytes with `no-store`, exact length and a
closed connection; an empty semantic MIME becomes `application/octet-stream` only in the transport
header. Query, Range and transfer framing remain rejected, and presentation filenames never enter
the route or file path. The v5 asset and custom-emoji routes reuse the existing grants and bytes.

## Worker verification

- Before implementation, a real contained request to `/v5/snapshot` returned HTTP 404 schema 1
  `unsupported`, establishing the absent v5 route red. The disposable World was created under a
  temporary directory and removed when the probe exited.
- `artifacts/ticket103-focused.xml` retains 78 passing real bridge, callback and World cases with
  `ResourceWarning` promoted to an error. Three new HTTP cases compare complete mixed
  document/photo/custom-emoji snapshots, changes, callbacks and sends without calling the handler's
  projection methods for expected output. They cover document IDs 2, 10 and signed-64-bit maximum,
  frozen callback GET/POST retry after later activity, persistence/reopen, MIME fallback, retained
  v5 assets/custom emoji, capability and World isolation, identical unavailable responses, strict
  syntax/query/Range/header/body framing, and complete logical-state preservation on rejection.
- Scoped Ruff check/format and strict mypy pass `src/gramlab/client_bridge.py` and
  `tests/test_document_bridge.py`. The environment was created separately in this checkout from
  offline cached packages. No guest, build, full gate, network, dependency or source export ran.
- Follow-up review found that the first route parser used only the final path segment: a real HTTP
  control proved `/v5/documents/extra/1` returned HTTP 200 and the granted ID-1 bytes. The corrected
  handler validates the complete suffix after `/v5/documents/`; nested, doubled and trailing slash
  variants now return schema-5 invalid-ID errors without changing the logical database.
  `artifacts/ticket103-route-followup.xml` retains all 78 affected cases passing with fatal
  `ResourceWarning`. Named blank and nonblank query parameters reject. A bare trailing `?` remains
  equivalent to no query because `urlsplit` exposes both as an empty query; the real granted-byte
  control passes, matching the inherited bridge parsing distinction.

This bridge slice does not establish Android document delivery or rendering. Default content
classification, document edits and albums remain outside this batch, so ordinary-file HTTP support
does not complete the operational milestone.

Reproduction uses the checkout-local environment and the outer network guard:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/python -m pytest -q -W error::ResourceWarning \
  --junitxml=artifacts/ticket103-focused.xml tests/test_document_bridge.py \
  tests/test_client_bridge.py tests/test_media_bridge.py tests/test_custom_emoji_bridge.py \
  tests/test_rich_mentions_bridge.py tests/test_callbacks.py tests/test_document_world.py \
  tests/test_document_storage_migration.py'
tools/dev default --offline --command .venv/bin/python -m ruff check \
  src/gramlab/client_bridge.py tests/test_document_bridge.py
tools/dev default --offline --command .venv/bin/python -m ruff format --check \
  src/gramlab/client_bridge.py tests/test_document_bridge.py
tools/dev default --offline --command env MYPYPATH=tests .venv/bin/python -m mypy --strict \
  src/gramlab/client_bridge.py tests/test_document_bridge.py
```

Primary integration passes the same78 affected checks with fatal ResourceWarning plus strict
Mypy/Ruff. JUnit document-bridge-integrated-01.xml is retained. Combined verification remains.

## Integrated acceptance

Core16 passes all 1,126 non-Android cases at 88.02% coverage on the integrated branch;
static15 passes all 64 documented commands and configuration/links in 259 Markdown files.
The retained core16 JUnit, log and outcome establish combined verification after this slice.
This resolves the assigned slice, preserving its focused acceptance and earlier failed evidence.
It does not establish Android document loading, default classification, edits or albums.
