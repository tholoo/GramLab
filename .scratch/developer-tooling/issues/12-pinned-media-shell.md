# Reproduce media fixtures with pinned developer tools

Type: task
Status: resolved
Work state: completed
Blocked by: none; normal runtime media architecture is separate

The original custom-emoji fixtures currently require a host FFmpeg installation and cannot name
its linked codec revisions. The user requested a high-quality flake/direnv environment and reusable
developer tooling. Add an optional media shell under the existing nixpkgs pin so fixture generation
and verification are reproducible without unrelated host packages. This is development tooling,
not approval of World storage, media delivery or emoji admission.

The pinned `pkgs.ffmpeg_6` is version 6.1.6, enables libvpx/libwebp, and uses libvpx 1.16.0 and
libwebp 1.6.0. Prefer that package over the broader full variant. Do not change the nixpkgs lock,
core shell packages, Android toolchain, existing runtime profiles or runtime network rules.
The coordinator owns binary-cache provisioning; an offline build can otherwise attempt a large
source rebuild. Never provision another checkout's virtualenv.

## Assignment and shared contract

Worker owns this ticket, `flake.nix`, new `nix/media.nix`, `.envrc`, `tools/dev`, and
`tests/assets/custom-emoji/` on `task/pinned-media-shell`. Shared contributor/environment/handoff/CI
docs remain coordinator-owned. Read the handoff, parallel, testing and completion instructions;
use a separate worktree and return a frozen branch for coordinator integration.

- Add `devShells.<declared-system>.media` with common development tools and pinned FFmpeg/ffprobe.
  Add `media` to the helper and direnv selection, and watch the new Nix file. Invalid names still
  fail explicitly; shell entry does not run an encoder, sync dependencies or launch a runtime.
- Export `GRAMLAB_MEDIA_TOOLCHAIN` pointing to generated JSON with schema 1, `nixpkgs_revision`,
  `package` (`ffmpeg_6`), `versions` (`ffmpeg`, `libvpx`, `libwebp`) and `executables` (`ffmpeg`,
  `ffprobe`). Executable store paths belong in that generated profile, not committed fixture data.
- Have the fixture tooling consume this optional profile and record only its portable version,
  package and nixpkgs data alongside the actual FFmpeg/libavcodec observations. Validate selected
  encoder/decoder paths against the profile before claiming its provenance; explicit overrides
  or PATH substitution must not falsely label another binary as pinned. Without a profile, retain
  honest unpinned-tool reporting rather than inventing versions. Document precise invocation.
- Keep the independently specified image geometry, transparency, colors, frame rate, duration,
  invalid-input expectations and encoder flags unchanged. Regenerate the manifest under the new
  profile; report any changed binary hashes for coordinator review before replacing accepted blobs.
  Keep original fixtures/failed observations reachable in Git and ignored evidence.

## Acceptance

The coordinator retains the current `tools/dev media` exit-2 rejection as the missing-feature
baseline. Prove real media-shell execution, expected tool versions, helper exit propagation and
its per-worktree retained Nix root. Verify direnv selection through its actual Bash evaluation
with controlled helper functions; unknown shell values must fail. Run Bash/ShellCheck, Nix format,
all-declared-platform evaluation and relevant host Nix checks. Evaluation is not a cross-platform
build or fixture-reproduction claim.

Repeat asset generation and direct decoding within the existing network guard under the pinned
media shell. Compare all old/new fixture hashes; verify full decoded geometry, exact static colors,
four transparent video frames and the one-second duration. Test a mismatched profile/tool override
rejects before any encoding or provenance publication. Run the existing focused Python static
checks; no new normal pytest inventory or Android guest is required for these tooling changes.
The coordinator owns independent browser checks if fixture bytes change and verifies that the
default/Android runtime profile digests and immutable native APK are unchanged.

## Worker evidence

The optional media shell reports FFmpeg/ffprobe 6.1.6, libvpx 1.16.0 and libwebp 1.6.0 from the
pinned nixpkgs revision. Guarded generation preserves all four accepted binary hashes; the manifest
now adds portable pinned provenance. Guarded decoding verifies the complete static/video geometry,
colors, alpha, four frames, one-second duration and malformed-file rejection. A mismatched active
profile exits before creating files. Focused shell/Nix/Python static checks and all-platform
evaluation pass. The first offline host checks lacked a Bash development output and attempted
transitive source builds. This was missing provisioning, not evidence that unrelated checks were selected. The
coordinator inspected the binary-cache plan and provisioned the missing output separately.

## Integrated acceptance

The coordinator independently repeated generation and decoding in a network namespace, checked
all four unchanged binary hashes against the retained baseline, rejected an incompatible encoder
with zero output files, and verified portable manifest provenance. Default/Android runtime profile
and immutable APK digests remain unchanged. The retained browser decode evidence still applies to
the identical bytes; this tooling change requires no new Android gate.

Actual media-shell entry and retained per-worktree profile, helper exit propagation, controlled
direnv selection/rejection, Bash/ShellCheck, Nix formatting, scoped Ruff and strict typing pass.
All three explicit host flake checks pass after provisioning. All declared platforms evaluate;
Only the host shell and encoding were executed. Coordinator configuration/link validation covers
162 Markdown files. Exact local commands, terminal outcomes
and the failed provisioning attempts remain in ignored evidence.
