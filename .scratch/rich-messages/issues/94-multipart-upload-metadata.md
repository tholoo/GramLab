# Preserve multipart upload metadata for document delivery

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

Own this ticket, `src/gramlab/bot_api.py`, and new `tests/test_multipart_uploads.py` only.
No World/storage/native/API-method additions, existing test edits, limits/admission changes,
network policy, dependencies, fixture or shared-doc changes. Coordinator owns integration.

The current multipart decoder recognizes filename-bearing parts but discards filename and part
Content-Type, returning only bytes. General documents need this metadata alongside exact bytes.
Preserve it now without deciding MIME detection or exposing sendDocument before it works.

Within the existing Bot API module, define a small immutable upload value with `data: bytes`,
`filename: str`, and `content_type: str | None`. A present empty filename remains an uploaded file;
an absent filename remains a text field. Preserve decoded filename and the existing parser's
trimmed Content-Type value exactly, including case/parameters and the distinction between missing
and present-empty type. Do not sanitize a filename into a path, infer MIME, reject new metadata
forms, or copy client-derived logic. Existing strict header/body/part/aggregate limits and error
behavior remain unchanged. No additional payload copy is needed.

`_multipart` returns its existing text fields plus named immutable upload values. Carry those
values through the HTTP handler into `_dispatch`. At the current byte-only photo/rich-photo/edit
World calls, project only `.data` into the existing `Mapping[str, bytes]` interface. Preserve every
attachment key and existing duplicate/unused-attachment rejection. Direct World callers remain
source-compatible. Keep parser complexity in the existing module rather than adding a redundant
public wrapper or compatibility overload; future document dispatch will consume the metadata.

Write a red at the decoder interface using literal bounded multipart bytes and independently
specified complete fields/upload metadata/bytes. Exercise Persian/Unicode filenames, empty names,
absent/empty/parameterized Content-Type, arbitrary binary bodies and multiple distinguishable
parts. Include the existing meaningful malformed/duplicate/nested/boundary/part-count/size/UTF-8
admission cases without silently broadening them. Full output comparisons should fail on dropped
or conflated metadata, altered bytes or unexpected text/file classification. These parser tests
are preparation evidence, not public document support.

Run the actual isolated existing media HTTP and real-bot round-trip tests plus new focused parser
controls and scoped lint/format/strict typing. No guest/build/full gate. Preserve red/green and
verify assigned imports. Return clean frozen tip, precise checks, metadata semantics, remaining
unsupported document behavior, source scope and terminal resources. Avoid upstream exports;
provision only the assigned small environment using its own tools/dev.

## Implemented boundary and evidence

The multipart decoder now returns frozen upload values containing the exact body bytes, decoded
filename and optional trimmed part Content-Type. Missing and present-empty Content-Type remain
distinct, filenames are not interpreted as paths, and case and parameters are preserved. The HTTP
handler carries these values into dispatch; existing photo and rich-photo World operations receive
only a same-key mapping of each value's original bytes.

The retained decoder red in `artifacts/ticket94-worker/red.xml` has one metadata failure while all
seven admission controls pass: current uploads are bare bytes and have no filename or Content-Type.
The final isolated run in `artifacts/ticket94-worker/final.xml` passes 12 multipart, media HTTP and
real-bot round-trip checks. It covers Unicode and empty filenames, missing/empty/parameterized types,
arbitrary binary bodies, multiple parts, immutability and the existing malformed, duplicate, nested,
boundary, part-count, aggregate-size and UTF-8 rejection boundaries. Scoped Ruff lint/format and
strict mypy pass for both owned Python files.

No World, storage, native or API-method behavior changed. General document methods remain
unsupported; this metadata is preparation for their separately reviewed implementation.

Coordinator integration of frozen530133e passes all12 affected parser/mediaHTTP/contained-bot
checks in 5.54 seconds, plus scoped lint/format/strict typing. Contributor and CI commands now
include the new parser scope. Evidence: `artifacts/multipart-metadata-integrated-01.xml`.
This preserves upload metadata and existing photo behavior; document support remains pending.

## Answer

Integrated acceptance is complete for this metadata-only ticket: all 12 affected checks and the
combined core10 gate pass (948 tests, 87.25% coverage, 189.00 seconds). All 55 documented static
commands pass. General document APIs, metadata projection and albums remain separate required work.
