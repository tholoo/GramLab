# Consumer runtime profiles

## Notes

- The current runner always launches every bot with `profile.python` and the same profile closure.
- Consumer bots may use independent locked environments whose dependencies are absent from
  GramLab's default profile.

## Decisions so far

- Runtime-profile paths remain trusted CLI/Python arguments, not consumer manifest data.
- The supervisor may mount the union needed to create child mounts; each bot child receives only
  its selected profile.

## Fog

- Each consumer project still owns how it provisions an immutable runtime profile.

## Tickets

- [01: Per-bot runtime profiles](issues/01-per-bot-runtime-profiles.md) — resolved.
- [02: Consumer rich-message compatibility](issues/02-consumer-rich-message-compatibility.md)
  — resolved.
