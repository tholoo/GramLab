# Project typed ordinary documents into original Android carriers

Type: task
Status: in-progress
Work state: claimed
Owner: task/ordinary-document-native-codec
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

## Comments

Worker implementation at the assigned base adds only the new-file patch, series entry, bounded GPL
reflection fixture, host probe collector and focused acceptance test. Private zero-fuzz staging status
is `ready`; the patch SHA-256 is
`94ff7ff25fa88578486dd2065acdcad4a33adfcec42a2ec0ce766dfd5a7b88b8`, and the staged
`GramLabDocument.java` SHA-256 is
`9a6107581f9beeda22fd179441492c95dd6e69efa94a5645f27c063389d8c449`. The final fixture compiles
with `javac -Xlint:all -Werror` and D8; its probe APK SHA-256 is
`799de74e1dd0e131c86be5187f0ae0a77a0c4626ab8415651895d979390f33b9`. Focused Ruff, strict
Mypy and two non-Android tests pass. The worker did not build an APK or run a guest. The required
pre-0029 missing-class red and post-0029 real `TLRPC`/`NativeByteBuffer` green remain coordinator
acceptance, so this ticket stays claimed until integration succeeds.

Review follow-up binds every parsed `Entry` field to independent literals before projection,
including distinct `a`/`b`/`c`/`d`/`e` SHA-256 values, and requires the pulled native
`summary.json` to parse exactly equal to process stdout. A disagreement host control rejects. The
updated fixture source SHA-256 is
`c8faa83decccee5a5bd1d3d0fe9b75daf81b286a42a8286d7ebe3e038a0178bb`; retained probe04 APK
SHA-256 is `d32f21950413e179fa7a2c72a92b17ecdfe8e1cb74382c6fc43ac04addd7511a`.
Probe03 remains retained as prior evidence. Updated focused Ruff, formatting, strict Mypy,
ShellCheck, and three non-Android tests pass; native execution remains coordinator-owned.


## Coordinator native checkpoint

The integrated host probe passes three cases; its patch-order follow-up additionally preserves
future queue appends. Normal29 compiles offline in2m39s, with exact staged codec source/provenance.
Probe04 is bound to reviewed Java/compiler/API/DEX/APK hashes. Fresh normal29 native02 returns
complete matching stdout/pulled summaries:33 of34 cases pass, but numeric_ordering_and_projection
fails as InvocationTargetException before any described carrier is retained. The fixture currently
hides its underlying cause. Probe-only bounded diagnostic follow-up is assigned; no production
codec defect has been demonstrated. The prior normal28 native01 exited137 with empty stdout and
Killed stderr; its initiator is unknown and this is not the intended missing-class regression red.
Original results remain retained; actual native acceptance and combined gate closure remain open.

Probe-only diagnostic follow-up preserves the successful 34-case result while failure records now
identify the exact projection/reflection stage and retain at most eight bounded causes and four
relevant stack frames. A missing bootstrap class produces a structured one-case `summary.json` and
matching stdout before native-library loading. This does not attribute the earlier status 137 to a
specific initiator. The fixture source SHA-256 is
`dabed8fa2691cd00d360fdc4b1ea1ee22046494957a406b7a8a977847da64538`; retained probe05 APK
SHA-256 is `df64f3597b1f55042f1e9585b2efe89bc53c7610c98ea2eeaa03d779175881e7`, with inputs manifest
SHA-256 `97cb282debf2071ac3b58f219404f18c8ca6489447295e89a0fc2109e4417c8c`. Java compilation with
`-Xlint:all -Werror`, D8, and three focused non-Android tests pass. Native diagnostic execution
remains coordinator-owned.
