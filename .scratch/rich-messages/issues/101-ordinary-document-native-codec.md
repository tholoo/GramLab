# Project typed ordinary documents into original Android carriers

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

Implement the independently testable ordinary-document descriptor/carrier prerequisite from the
[frozen contract](../../../docs/development/documents-implementation-contract.md) and
[pinned native source review](../../../docs/development/documents-references.md). This is one
required part of file delivery, not complete native document support. Loader, v5 negotiation,
message application, original download controls and real-bot acceptance remain required.

## Ownership and interface

Own this ticket; new patch `clients/android/patches/0029-ordinary-document-codec.patch`; append
only to `clients/android/patches/series`; new `tests/test_android_document_codec.py`,
`tests/probes/android_document_codec.py` and bounded GPL fixtures in
`tests/fixtures/android_document_codec/`. Root owns shared docs, live source, APK builds and native
runs. Never modify an existing patch, existing Java class or another worker's files. Generate a
minimal new-file patch; no upstream export or source acquisition is needed.

Add GPL class `org.telegram.gramlab.GramLabDocument` with immutable nested `Entry` containing
positive `long id`, `long size`, and `String fileName`, `mimeType`, `sha256`. Public static
`identifier(Object)` accepts only canonical positive decimal strings through Long.MAX_VALUE.
Public static `parse(JSONArray)` returns a `Map<Long, Entry>` in strictly increasing numeric ID
order; reject duplicate/out-of-order rows, wrong types, missing/extra fields and malformed metadata.
The exact five descriptor fields are document_id, file_name, mime_type, file_size and sha256.
Filename is already normalized: preserve its Unicode exactly, require valid paired UTF-16,
nonempty, at most81 Unicode code points, and no slash/backslash/NUL. MIME may be empty; otherwise
require a bounded ASCII MIME type/subtype (maximum256 characters, no parameters or whitespace).
Size is an actual integer JSON number,1 through50,000,000 inclusive; reject floats, Booleans and
strings. SHA-256 is exactly64 lowercase hex digits. Do not sniff bytes or rederive MIME/filenames.

Public static `project(Entry)` constructs the actual pinned `TLRPC.TL_document`: id=-Entry.id,
dc_id=-1, access_hash=0, empty file_reference, date=0, unchanged MIME and size, no thumbnail/video
thumbnail flags, and exactly the original filename attribute. Do not add sticker/audio/video/image
attributes or dimensions. This preserves the force-file carrier contract. The ordinary negative-ID
namespace must remain disjoint from positive custom emoji, including2147483648 and Long.MAX_VALUE.
This class must have no global cache, activation mutation, I/O or networking. Later coordinated
bridge code will validate dependencies before committing them and supply Entries to this codec.

## Acceptance

Follow TESTING.md, licensing/upstream and parallel guidance. Use literal source-derived expected
JSON plus an actual Android app_process probe that loads the original TLRPC classes, projects,
serializes/deserializes and describes the complete original carrier. Cover empty MIME, Unicode
filename, exact size/ID boundaries, mixed numeric ordering, all malformed descriptor controls,
ordinary versus custom-emoji IDs, original attachment keys and the2147483648 sentinel. Preserve
full 64-bit values through NativeByteBuffer. No stand-in TLRPC implementation or generated oracle
from the production codec. Reflection may call the real new class; it must not recreate parsing or
serialization logic. Retain GPL fixture notices.

Worker may compile the bounded probe using existing pinned Java/Android tools and perform minimal
patch-stage plus focused host/static checks. Root performs the old-APK missing-codec red, new-APK
actual native green and full subsequent integration. Clearly label unavailable native coverage.
No full APK build, guest, network, dependency changes, full gate or large source copy. Keep temporary
data small; return a clean actual Git hash, focused results and terminal processes.
