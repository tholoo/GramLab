# Pin the rich-photo contract before proposing asset delivery

Type: task
Status: ready-for-agent
Work state: ready for isolated research worker
Blocked by: none for source research; public asset/delivery design requires user consultation

Use the research skill and follow the parallel workflow in a dedicated `task/rich-photo-contract`
checkout. Own only this ticket and `docs/development/rich-photo-references.md`. Coordinator owns
architecture proposals, public interfaces, other docs and implementation. No source/assets are to
be imported into the MIT simulator. Read licensing/upstream guidance before inspecting sources.

Investigate the smallest useful static photo rich block against pinned official Bot API/server,
TDLib and Telegram Android sources already referenced by this repository. Follow claims to their
owning primary source; browse official/pinned sources only when local acquired material is missing.
Reference research access never authorizes bot/client external traffic. Do not provision packages,
build an APK, launch a guest or contact a DC/account.

Record exact Bot API photo block input/output fields, upload/file-reference rules, validation and
normalization relevant to one original PNG, and exact native rich photo block/Photo/PhotoSize
projection requirements. Inspect original RichPhotoBlock, ImageReceiver and FileLoader local-byte
resolution: identify the smallest faithful on-demand delivery boundary and rejected/missing-file
behavior, distinguishing source facts from design inference. Include immutable commit/file links
where available and clearly identify any moving official documentation.

State which seams are absent in GramLab today and list consequential decisions still needing user
consultation: asset identity/lifetime, upload/registration shape, authenticated local-byte delivery,
cache/loading semantics and scope. Do not choose those interfaces or lower the fidelity target.
The coordinator needs a concrete proposal that can split core validation/storage, GPL delivery and
real-bot native acceptance after approval. A generated PNG fixture worker is independent; no
fixture filename is a proposed public media ID.

Write one concise source-backed Markdown findings file. Validate local links and changed-tree
privacy, commit only owned files, and return a clean frozen branch with primary-source references,
verified facts, unresolved questions and terminal tool/resource state. No implementation support
or native fidelity is claimed from this research.
