---
name: create-prompt-skill
description: Create or revise a data-only Local Prompt Studio Skill for a specific image, video, audio, or language model. Use when the user supplies model documentation or prompt requirements and wants a reviewable SKILL.md package, references, output contract, provenance, and synthetic validation fixtures; also use when converting a hard-coded prompt writer into a model-specific Skill.
---

# Create Prompt Skill

Build a concise, reviewable package that teaches a configured language model to write prompts
for one target model or workflow. Never execute or add Skill scripts.

## Workflow

1. Establish the target model and version, two or three concrete user requests, expected output
   shape, attachment syntax, and known failure cases.
2. Inspect the supplied source material. Record its title, URL or local path, retrieval date, and
   license or redistribution status. Do not copy third-party documentation into a public package
   unless the user has redistribution rights.
3. Read [references/package-format.md](references/package-format.md) before creating files.
4. Create the smallest sufficient package. Keep procedure in `SKILL.md`; put detailed syntax or
   vocabulary in directly referenced files under `references/`. Avoid duplicating content.
5. Express machine-checkable requirements in `contract.json`. Do not use a contract as a claim
   that the output is safe, factual, high quality, or accepted by the target provider.
6. Add synthetic fixtures that contain no private prompts, copyrighted media, secrets, or unsafe
   requests. Include one valid expected output and at least one intentionally invalid output when
   the contract is nontrivial.
7. Run Local Prompt Studio's `--inspect-skill` and `--validate-only` commands. Fix every structural
   failure. If an inference server is already available, run one ordinary request with `--no-save`;
   do not start or download a large model without user approval.
8. Report source rights, files created, checks run, limitations, and any behavior that still needs
   human or model-specific review.

## Authoring rules

- Use a lowercase hyphenated package name under 64 characters.
- Give `SKILL.md` frontmatter exactly `name` and `description`; make the description state both
  what the Skill does and when it applies.
- Write imperative instructions and return-format requirements. Tell the writer model to preserve
  explicit user constraints and distinguish sourced facts from creative additions.
- Keep the Skill specific to one model family or stable prompt dialect. Create variants instead
  of silently mixing incompatible versions.
- Use `@image_0`, `@image_1`, and so on only when the target workflow uses that convention and
  attachments exist.
- Never frame the Skill as bypassing safeguards, policy, licensing, authentication, or access
  restrictions.
- For a public package, independently author examples and summaries. Prefer links plus provenance
  over copied source text.
