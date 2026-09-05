# Android client integration

Target: a pinned, minimally patched build of [Telegram Android](https://github.com/DrKLO/Telegram),
with real upstream UI/controllers and a dedicated local simulation bridge.

**Not implemented:** no upstream checkout, copied client code, APK, Gradle wrapper or Android
runtime is included. This directory's original notes are MIT; acquired/adapted Android code and
patches must carry their applicable upstream terms. See [licensing](../../docs/development/licensing.md).

The next agent must validate the request/update boundary, synthetic identity initialization,
media loading, reset/recovery, semantic input and independent egress blocking before committing
to the adapter's public interface. Replacing one Java method is not sufficient network isolation.

Place a verified checkout in ignored `upstream/`, pinned by a committed provenance manifest when
acquired. Keep ordered, reviewable changes in `patches/`; document each reason and upstream
applicability. Do not silently track master, reuse real sessions, or ship upstream release keys.

Use distinctly unofficial GramLab branding without changing the in-chat rendering contract.
Prefer emulator profiles for reproducibility. Waydroid is not required for the scaffold and is
not currently a supported or tested runtime; evaluate it separately if useful on the host.
