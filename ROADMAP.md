# Roadmap

The roadmap is intentionally small enough for one active maintainer. Priorities may change in
response to real issue reports.

## 0.1 — public alpha

- [x] Safe directory, file, and ZIP Skill loading
- [x] Skill inspection and optional output contracts
- [x] OpenAI-compatible streaming client with same-turn continuation
- [x] CLI, desktop UI, local history, and unit tests
- [ ] Publish compatibility reports for at least two local servers (LM Studio: complete)
- [ ] Add signed release artifacts and a reproducible release checklist

## 0.2 — community Skills

- [x] Define version 1 Skill manifest and output-contract JSON Schemas
- [x] Validate version, provenance, length guards, and bounded pattern inputs with clear diagnostics
- [x] Add a Codex authoring Skill that produces a reviewable starter package
- [ ] Add a conformance test command for community Skill maintainers
- [x] Document licensing and provenance metadata for shared Skills
- [x] Add a bounded, data-only tag-list contract and an independently authored illustration-tag
  example without model assets or vendor guides

## Later, only with evidence

- Sandboxed adapters for server-specific capabilities
- Optional redaction rules for saved history
- Accessibility and localization improvements to the desktop UI
- A curated Skill index with review and revocation procedures

Executing arbitrary Skill code or silently downloading models is not planned.
