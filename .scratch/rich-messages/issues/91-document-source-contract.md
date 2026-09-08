# Pin general-document API and native mapping requirements

Type: research
Status: ready-for-agent
Work state: resolved
Blocked by: source review and later interface decisions

Own this ticket and one new `docs/development/documents-references.md` only. Read the research
skill, current handoff, operational milestone, approved media proposal/contract, licensing/upstream
maintenance and parallel workflow. Work from pinned primary official Bot API and Telegram Android
sources; distinguish local extensions and production rules from approved synthetic semantics.
Do not copy client-derived implementation into the MIT core. Keep quotes short and cite exact
source/version/section links. Machine paths belong only in ignored notes.

Establish the ordinary `sendDocument` upload/reuse/download/message/caption/keyboard contract,
relevant multipart filename/MIME semantics and limits, and the original Android document object's
required fields/attributes and FileLoader location/cache mapping. Identify which existing asset,
bot file identity, grant, HTTP download and client dependency mechanisms can be reused. The current
image-only dimensions/descriptors must not be silently widened; describe concrete schema/version
choices needing a follow-up freeze. Report unknowns explicitly and propose a bounded first document
profile with clearly labeled recommendations, not unapproved implementation decisions.

Keep albums distinct: summarize required atomic grouping/identity/message ordering and native
layout dependencies only far enough to avoid designing documents into a dead end. Do not replace
albums with repeated single sends. No implementation, ADR changes, fixtures, new dependencies,
credentials, external runtime execution, Android build/guest or full gate. Source research may use
primary web documentation separately from runtime. Return a reviewed factual note, exact sources,
open decisions and suggested independent implementation scopes on a clean frozen branch.

## Answer

Pinned findings and bounded recommendations are recorded in
[`docs/development/documents-references.md`](../../../docs/development/documents-references.md).
Ordinary documents can reuse the immutable-byte, bot-file, recipient-grant, authenticated download
and original loader lifecycle concepts, but the current image-only storage/descriptors and
bytes-only multipart output cannot represent document filename/MIME metadata. ADR 0005 already
governs World ownership, grants, bot identity, retention, versioned dependencies and original
loading. The pinned path cleans the multipart filename, derives MIME from its extension, ignores
the part content type for semantic metadata, rejects zero bytes, and maps the detection flag to
Telegram's `force_file`. The remaining compatibility gap is Telegram-server classification and
metadata rewriting when detection is enabled, plus the operational size ceiling and exact album
failure/group identity semantics. A 10 MB forced-file path is only an incomplete implementation
probe. General files and atomic 2–10 document albums remain required, including the normal
detection default, reuse/download, ordered shared group identity and native document-group layout.
