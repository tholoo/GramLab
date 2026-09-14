# Changelog

All notable changes to the published Python package are recorded here.

## Unreleased

## 0.1.0a2 - 2026-09-14

- Add a resettable persistent playground with authenticated status, send, tap, capture, add-bot,
  reset and stop controls over a real running consumer.
- Add an interactive Android mode that exposes the contained original Telegram client through a
  separately isolated scrcpy viewer and one explicitly selected display socket.
- Model synthetic group conversations and member changes across semantic and original-client
  input, rendering and recovery paths.
- Preserve current rich-button targets and effects across client restarts, consumer interruption,
  unrelated edits and complete-state reconciliation.
- Let trusted callers select an independently provisioned runtime profile for each declared bot,
  while retaining GramLab's own profile for the scenario and supervisor.
- Record per-bot runtime fingerprints and keep profile dependency closures isolated between bot
  components.
- Start playground consumers and semantic setup while Android boots, switch later interaction to
  the native client, and avoid restarting the client for same-persona navigation.

## 0.1.0a1 - 2026-09-13

First experimental prerelease.

- Run real local Telegram bots against deterministic, isolated World state without Telegram
  credentials or production network access.
- Author scenarios through typed users, configured bots, conversations, messages, callbacks,
  captures and bounded observation waits.
- Exercise simulation-only and separately configured original-Android rendering workflows through
  the `gramlab` command-line runner.
- Model ordinary and rich messages, callbacks, photos, documents, albums and custom emoji within
  the documented compatibility boundaries.

The public Python interface is experimental. Python 3.13 on supported Linux hosts is required;
Android tooling and APKs are not distributed in the Python package.
