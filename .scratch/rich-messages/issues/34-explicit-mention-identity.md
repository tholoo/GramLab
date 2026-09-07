# Review explicit rich-mention identity and visibility

Type: feature
Status: needs-triage
Work state: concrete proposal prepared; awaiting consultation
Blocked by: user review of identity disclosure and bridge versioning

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
