# Consumer runtime profiles

GramLab's consumer runner must execute a real bot with the bot's own already-provisioned runtime
dependencies. The trusted caller may select a separate runtime profile for each declared bot while
the scenario and supervisor continue to use GramLab's profile.

The profiles are provisioning inputs, never manifest-controlled paths. Runtime execution remains
offline. Each bot component sees only its own profile closure plus its staged `/work`; the outer
trusted supervisor receives the union required to create those nested mounts. Default runs without
bot-profile overrides remain byte-for-byte compatible at the manifest and result boundaries.

## Acceptance

- Python callers and the CLI can bind a trusted runtime profile to a declared bot alias.
- A selected bot launches with that profile's Python and dependency closure.
- Different bots can use different profiles without seeing one another's profile-only files.
- Unknown aliases, duplicate CLI bindings and invalid/missing profile inputs fail before output
  creation or consumer execution.
- Results record a SHA-256 fingerprint for every selected bot runtime profile without exposing
  machine-local profile paths in portable source inputs.
- Existing single-profile consumers continue to pass unchanged.
- Focused behavioral tests exercise a real contained bot dependency unavailable from GramLab's
  default runtime, plus rejection and isolation cases.

Mini Apps, arbitrary manifest commands, dependency installation, mutable host mounts and consumer
environment inheritance are out of scope.
