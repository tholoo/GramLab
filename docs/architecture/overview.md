# Architectural boundaries

Status: approved direction, not a proven implementation. Public module APIs, bridge protocol,
storage engine and runtime orchestrator are deliberately undecided pending the first milestone.

## Independent simulator

The Python core owns simulated worlds: identity, chats, permissions, messages, update delivery,
assets, time and fault schedules. A local HTTP Bot API surface lets real bot processes participate.
The SDK and future CLI control scenarios through the same owned state, rather than maintaining
separate UI and API simulations. Independently written core/SDK code is MIT-licensed.

Bot API compatibility is not MTProto wire-server compatibility. A native Telethon/Pyrogram client
cannot simply use this HTTP endpoint. A generic MTProto server is outside the agreed foundation;
consult the user before expanding into that product.

## Android adapter

Retain Telegram Android's actual rendering, interaction and controller behavior where practical.
Validate a small patch surface that replaces request/response/update exchange with a local bridge
and supplies synthetic identity/media. Keep client-derived implementation in the copyleft boundary.
Do not copy Android classes or generated client-derived schema code into the MIT core without a
proven compatible license/provenance decision.

The bridge must map Bot API concepts and the client's Telegram API objects into one world. Shared
state alone does not establish correct mapping; use independently derived contract fixtures.
Startup/native networking, uploads/downloads, DNS fallback, push and WebViews need separate audits.
Enforce egress outside the patched application as well as inside its adapters.

## Modes and isolation

Simulation-only tests have no Android runtime. Headless Android still renders inside a runtime;
interactive Android exposes that same UI for review. Replay a compatible scenario through each
mode and compare semantic outcomes; only rendered modes produce client-fidelity evidence.

Allocate one isolated world and artifact namespace per run. A small pool of isolated Android
instances can observe selected personas while many virtual users act without rendering. Bound
worker counts by measured host resources. Multiple renderer instances in one world must agree on
state; different worlds must not share messages, media IDs, clocks, update queues or consumer DBs.

## Deferred implementation decisions

The next agent must provide evidence and consult the user before fixing consequential choices:
exact upstream revision/runtime baseline, bridge and schema provenance, storage/replay strategy,
runtime provisioning, process isolation and distribution packaging. A feasibility finding is not
permission to switch to Web/Desktop, approximate the UI, contact real DCs or adopt a different
license strategy. The first ticket bounds this investigation rather than leaving it unstructured.
