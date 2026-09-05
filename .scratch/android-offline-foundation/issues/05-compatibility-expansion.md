# Derive the versioned compatibility catalog and expansion tickets

Type: research
Status: needs-info
Work state: open
Blocked by: 01

Inventory the selected official Bot API, client schema, Android UI and relevant configuration
surfaces. Turn remaining product requirements into individual bounded Markdown tickets, informed
by foundation findings. Do not hard-code consumer application's games or treat it as the catalog source.

## Acceptance

- Enumerate methods/update types and meaningful chat/permission/client combinations, with sources.
- Distinguish rich-message API exposure from source-only rendering, and fixture emoji from actual
  entitlement/document existence. Cover Mini Apps and non-game bot features explicitly.
- Mark documented, observed, approximate and unsupported behavior separately from implementation.
- Include lifecycle, recovery, language, invalid actions, fault, UI and concurrency requirements.
- Identify any scope requiring a new user decision instead of inventing support.
- Keep first-milestone progress honest; the long-term catalog is not evidence of implemented code.

## Comments

This research may proceed alongside later implementation once the selected profile is known.
