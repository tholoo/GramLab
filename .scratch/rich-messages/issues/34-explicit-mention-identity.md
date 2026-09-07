# Review explicit rich-mention identity and visibility

The user explicitly approved all four prepared designs and then resumed the goal. This approval
supersedes the pending-consultation instructions retained below as proposal history. Proceed with
the recommended direction; freeze shared implementation contracts before parallel dispatch.

Type: feature
Status: ready-for-agent
Work state: design approved; implementation pending
Blocked by: none; user approved all four designs on 2026-09-07

The [proposal](../../../docs/development/rich-mention-proposal.md) separates Bot API input User
claims from authoritative output and original Android's numeric user carrier. It recommends
bot-contact admission, ID-only internal storage, message-derived persona visibility and version-3
dependency-first delivery. Full returned User objects remain admissible as input; their extra
profile fields do not override World identity.

This supports third-party mentions without making the whole World directory visible. The exact
synthetic accessibility/disclosure and versioning choices need consultation under AGENTS.md.
Do not implement them or record them as an approved ADR yet. After review, freeze response schemas,
error rules and ownership before parallel implementation. Current native gate inputs remain frozen;
source research/proposal preparation does not prove runtime mention support.
