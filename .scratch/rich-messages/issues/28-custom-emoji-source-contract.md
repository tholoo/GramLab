# Pin the custom-emoji boundary needed for operational readiness

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none for research; asset/API architecture remains subject to consultation

Research worker owns only this ticket and `docs/development/custom-emoji-references.md`, on
`task/custom-emoji-contract`. Follow the research skill, parallel workflow and licensing/upstream
guidance. Coordinator owns architecture, implementation, compatibility and handoff. No runtime,
account/DC, dependency acquisition or third-party asset import is assigned.

The first operational milestone requires custom emoji, while Mini Apps may follow later. Answer
three concrete questions from the existing pinned official Bot API, TDLib and Android sources:

1. What are the exact ordinary entity and rich-text input/output shapes and the relationship
   between `custom_emoji_id`, Bot API file identities and `getCustomEmojiStickers` results?
2. What minimal document metadata, attributes and locally authored static/animated asset formats
   does the pinned original Android renderer require? Identify the existing document/file-loader
   seam, separating source requirements from a proposed GramLab storage or delivery interface.
3. Which permission, premium, sticker-set or asset-availability conditions affect admission and
   presentation? Distinguish facts from unknown offline modeling choices; synthetic acceptance
   must not be described as real production entitlement.

Produce one concise cited memo with immutable source links, exact small example shapes, current
GramLab gaps and consequential decisions still open. Reuse local acquired/reference material.
External primary-reference lookup is allowed if needed; it never authorizes runtime egress.
Keep this bounded to the first document/rendering contract: record unresolved complete sticker
administration behavior instead of expanding into an exhaustive sticker-API project. Preserve
the agreed fidelity target and original renderer. Send decisive findings early.

Validate links/privacy/diff and commit only owned files, returning a clean frozen branch with
source-evidence limits and terminal resources. No compilation or runtime tests are needed for
a research-only document.

## Answer

Pinned findings are recorded in
[`docs/development/custom-emoji-references.md`](../../../docs/development/custom-emoji-references.md).
The boundary requires both entity support and a resolvable Android `Document`/media projection;
synthetic admission must remain explicitly separate from production Telegram entitlement.

Coordinator review checked the frozen branch, selected pinned server input/lookup and Android
static/animated loader paths, local links and privacy. The research is integrated; runtime
implementation and its consequential choices remain open.
