# Contributing

Thank you for improving Local Prompt Studio. Small, reviewable changes with tests are easiest
to maintain.

## Before opening a pull request

1. Search existing issues and describe the user-visible problem.
2. Keep the core model-neutral and dependency-light.
3. Add or update unit tests for behavior changes.
4. Run `python -m unittest discover -s tests -v` and `ruff check .`.
5. Update documentation when the CLI, Skill format, privacy behavior, or trust boundary changes.

## Skill contributions

Only contribute Skill material you wrote yourself or may legally redistribute. Include its
license and provenance in `skill.json` and the pull request. Validate new manifests against the
published v1 JSON Schemas. Do not copy a vendor's documentation into this
MIT-licensed repository merely because it is publicly readable. Prefer compact examples that
teach the format without endorsing one provider.

Skill packages must remain data-only. Pull requests that require Local Prompt Studio to execute
Skill scripts will not be accepted without a separate design and security review.

## Pull request checklist

- [ ] I have the right to contribute every changed file.
- [ ] No secrets, personal histories, model weights, or private media are included.
- [ ] Tests cover the changed behavior and pass locally.
- [ ] The change preserves local-first defaults or clearly documents any network behavior.
- [ ] User-facing changes are reflected in the English and Chinese documentation when relevant.

By contributing, you agree that your contribution is licensed under this repository's MIT
License.
