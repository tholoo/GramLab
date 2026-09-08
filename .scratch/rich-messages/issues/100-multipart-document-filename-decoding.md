# Decode multipart filename metadata before document normalization

Type: task
Status: in-progress
Work state: claimed
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

Claimed by the assigned implementation worker. Scope remains the four assigned files; coordinator
owns integration and shared documentation. Reference research is read-only; runtime decoding will
use independently written quoted grammar and standard-library percent decoding.

## Implemented and verified

The existing quoted form-data profile now admits backslash-escaped quoted values and decodes
these values in the pinned order: quoted unescaping, one percent-decoding pass, UTF-8 metadata
interpretation. Plus signs remain literal; invalid/truncated percent pairs remain literal.
Duplicate and empty field-name checks use decoded names. Invalid field-name UTF-8 rejects;
invalid filename UTF-8 round-trips through internal surrogateescape and reaches the pinned
cleaner's literal `file` fallback. Filename presence, empty filenames, exact uploaded bytes,
missing/empty declared types, and existing framing/size/count limits remain distinct and unchanged.
No filename is opened as a path or published as a message, and photo dispatch still consumes only
upload bytes. There are no new API methods, World changes, dependencies or runtime network paths.

Reference facts were read from already retained TDLib revision
`bc9c263e2bfee06aaab41e82db51a103376030bc`: `tdnet/td/net/HttpReader.cpp:345–367`
(quoted escapes), line389 (decode with plus conversion disabled), and
`tdutils/td/utils/misc.cpp:172–190` (one valid-hex decoding pass). This is independent Python
implementation using standard-library percent decoding, not imported upstream source. Cleaner
expectations additionally follow `tdutils/td/utils/filesystem.cpp:108–130`: plus and percent are
allowed ASCII characters; quote/backslash are not. Complete header grammar and remote server
rewriting remain unclaimed.

The initial isolated run retained 23 failures and 7 passes in `artifacts/ticket100-red.xml`:
encoded names remained encoded, quoted escaped quotes rejected, malformed trailing escapes and
decoded-name collisions were accepted, and invalid raw filename UTF-8 failed prematurely.
Three literal cleaner expectations were corrected against pinned ASCII source before changing
production: plus and percent survive cleaning. The first combined run then passed 50 cases;
one new expected stored photo shape omitted the existing `text: ""` member. Its failure remains
in `artifacts/ticket100-green.xml`. The corrected final run passes all 51 cases in
`artifacts/ticket100-final.xml`.

The new 30 cases include 17 literal filename/cleaner cases, decoded Unicode field names with
unchanged text payloads, 11 malformed/collision controls, and real HTTP validation. The HTTP case
compares the entire SQLite logical state after each rejected request, then independently checks
the complete photo response, getFile response, downloaded original bytes, stored message and
asset descriptor. Existing multipart, photo HTTP and World checks retain the size/count/metadata,
photo reuse/edit and persistence coverage. Strict mypy, Ruff lint/format, checkout import identity
and Git diff checks pass.

Reproduction in the assigned pinned offline environment:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -q tests/test_multipart_filename_decoding.py tests/test_multipart_uploads.py tests/test_media_http.py tests/test_media_world.py --junitxml=artifacts/ticket100-final.xml'
tools/dev default --offline --command .venv/bin/mypy --strict \
  src/gramlab/bot_api.py tests/test_multipart_uploads.py tests/test_multipart_filename_decoding.py
.venv/bin/ruff check --no-cache src/gramlab/bot_api.py \
  tests/test_multipart_uploads.py tests/test_multipart_filename_decoding.py
.venv/bin/ruff format --check --no-cache src/gramlab/bot_api.py \
  tests/test_multipart_uploads.py tests/test_multipart_filename_decoding.py
```

The separate environment was provisioned offline using immutable hardlinked package archives and
separate writable cache metadata from the frozen metadata worker. No new source acquisition,
guest, Android build, full gate or upstream export ran. All task commands and HTTP servers are
terminal. Coordinator owns merging, shared contributor/compatibility documentation and subsequent
document API/World integration. `_Upload.filename` now always means decoded metadata; downstream
code must not percent-decode again or expose its possible surrogateescape values directly.
