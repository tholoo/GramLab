# Publish the experimental Python package

Status: ready-for-agent
Work state: claimed

Prepare and publish GramLab's independently written Python package without distributing the
separate GPL Android application, acquired upstream source, credentials or runtime artifacts.
The first release is an alpha and must preserve tested dependency and Python constraints rather
than widening compatibility without evidence.

## Acceptance

- `main` contains the resolved public scenario-flow interface and release metadata.
- Version `0.1.0a1` is built with source overrides disabled.
- Wheel and source archive install in isolation, expose the `gramlab` CLI and public typed API,
  contain the required MIT/Boost notices, and exclude Android/client/runtime artifacts.
- A tag-triggered GitHub workflow builds once, separates build and OIDC publication permissions,
  emits attestations and publishes only the retained build artifacts through PyPI Trusted
  Publishing.
- The GitHub `pypi` environment and matching pending PyPI publisher are configured before tagging.
- The pushed tag, GitHub release and PyPI project are verified after publication.

## Tickets

- [01: First Python prerelease](issues/01-first-python-prerelease.md)
