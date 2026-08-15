# Maintainer runbook

This runbook records the minimum evidence required for changes and releases. It is intentionally
short; public issues and pull requests remain the source of truth for individual decisions.

## Pull requests

1. Link the issue or explain why a small maintenance change needs none.
2. Confirm the diff contains no private prompts, histories, media, credentials, model weights, or
   third-party documentation without redistribution rights.
3. Require the stable `quality` check. It succeeds only after every Windows, macOS, and Linux test
   job passes on each supported Python version.
4. Review network, history, ZIP loading, path handling, and contract changes against
   [the security model](SECURITY_MODEL.md).
5. Squash or merge with a message that describes the user-visible outcome.

## Releases

1. Start from a clean, up-to-date `main` after the required `quality` check passes.
2. Run `ruff check .`, `python -m unittest discover -s tests -v`, every bundled Skill inspection,
   each example contract validation, and a wheel build.
3. Update `CHANGELOG.md`, the version in `pyproject.toml`, and compatibility notes when relevant.
4. Create an annotated semantic-version tag and GitHub release with limitations and verification
   results. Attach the wheel and its SHA-256 checksum.
5. Install the release artifact in a fresh virtual environment and run `--help` plus Skill
   inspection before announcing it.

## Branch protection

Protect `main` against force pushes and deletion. Require the `quality` status check before merge.
Because the project may have one active maintainer, do not claim an independent review occurred
when the founding maintainer reviewed their own change. Invite external review for security or
breaking changes and record it when it actually happens.
