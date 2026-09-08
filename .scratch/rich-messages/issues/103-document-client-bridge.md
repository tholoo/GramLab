# Deliver ordinary documents through authenticated version-5 client HTTP

Type: task
Status: ready-for-agent
Work state: open
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
