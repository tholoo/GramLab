# Decode multipart filename metadata before document normalization

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

Implement the independently resolved multipart metadata decoding prerequisite for ordinary files.
The [source contract](../../../docs/development/documents-references.md) pins TDLib's quoted-string
unescaping followed by one percent-decoding pass with literal plus signs. Existing upload94 keeps
raw filename/type metadata; metadata97 expects a decoded filename. Do not make World callers or
normalization helpers guess whether decoding already occurred.

## Ownership and boundary

Own this ticket, `src/gramlab/bot_api.py`, existing `tests/test_multipart_uploads.py` and new
`tests/test_multipart_filename_decoding.py`. No World/documents/client_bridge/native edits, new
methods/routes, request-limit changes, dependencies, lockfiles or shared docs. Coordinator owns
later sendDocument and HTTP/v5 integration after99. Keep all existing photo payload/result behavior.

Within the existing admitted quoted form-data disposition profile, handle backslash escaping of
quoted parameter values, then decode valid percent pairs once, case-insensitively. Preserve plus;
leave malformed/incomplete percent sequences unchanged. Perform duplicate/empty attachment-name
checks on the decoded field name. Preserve filename presence independently of its value. Empty
filenames remain uploads. Preserve declared content type exactly as currently recorded, including
missing versus empty. No byte sniffing or normalization belongs in this parser.

A filename's invalid decoded UTF-8 must survive as presentation input for the pinned cleaner's
`file` fallback, rather than be decoded with lossy replacement that produces another valid name.
Use reversible UTF-8 surrogateescape for the internal `_Upload.filename` string if needed; this
string must not become a host path or a public message. Decoded field names remain valid Unicode
names and invalid field-name UTF-8 rejects. Do not relax malformed framing/header, duplicate,
text-size, payload-size or part-count checks. The task does not claim complete support for every
upstream header grammar; unsupported header forms must continue to reject explicitly.

## Acceptance

Use literal byte multipart requests and independently source-derived expected metadata. Cover plus,
upper/lower percent pairs, one-pass escapes, percent-encoded separators, quoted escaped slash,
escaped quote/backslash, malformed/truncated escapes, empty filenames, invalid filename UTF-8 and
decoded-name collisions. Verify the decoder + pinned cleaner boundary with fixed expected names;
never use the implementation helper to generate an expected value. The existing photo HTTP path
must still publish and download exact bytes despite odd filenames/declared types. Invalid decoded
field names and malformed headers must fail before publication, with full unchanged World state.

Follow TESTING.md and parallel guidance. Source files already acquired for91/97 are read-only
reference inputs; no further network or upstream export is assigned. Run focused multipart and
photo HTTP/World checks plus Ruff/strict typing in the assigned pinned isolated environment.
Preserve red/green results, keep generated files bounded, and return a clean actual commit hash
with exact checked outcomes and terminal processes. Ordinary document API/default detection,
byte ceilings, bridge delivery and albums remain separate required work.
