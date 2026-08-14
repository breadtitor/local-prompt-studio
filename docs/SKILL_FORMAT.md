# Local Prompt Studio Skill format

A Skill is a data-only package that tells a language model how to transform a user's rough
request into a prompt for another model or workflow. Local Prompt Studio intentionally supports
a small subset centered on `SKILL.md`; it does not execute scripts or install dependencies.

## Minimal package

```text
my-skill/
└── SKILL.md
```

The whole UTF-8 Markdown file becomes model context. YAML-style frontmatter is optional; a
`name` value is used for display when present.

## References

When no manifest exists, supported text files under `references/` are loaded in sorted order:
`.md`, `.txt`, `.json`, `.yaml`, and `.yml`.

```text
my-skill/
├── SKILL.md
└── references/
    ├── output-format.md
    └── vocabulary.txt
```

## Local Prompt Studio manifest

An optional `skill.json` makes inclusion explicit:

```json
{
  "name": "Example Prompt Writer",
  "entrypoint": "SKILL.md",
  "include": ["references/output-format.md"],
  "contract": "contract.json"
}
```

All paths are relative to the package. Absolute paths and parent traversal (`..`) are rejected.
The manifest is an extension of Local Prompt Studio, not a claim of universal Skill-package
compatibility.

## Output contract

`contract.json` adds deterministic checks after generation:

```json
{
  "name": "Example contract v1",
  "required_sections": ["summary", "prompt", "constraints"],
  "min_output_chars": 120,
  "reference_pattern": "@image_(\\d+)",
  "reference_index_base": 0,
  "require_all_attachments_referenced": true
}
```

Section names are matched as case-insensitive headings followed by a colon. If
`required_sections` is supplied, their order is also checked. The reference regex must contain
one capture group for the numeric attachment index.

Contracts detect structural mistakes; they do not determine whether a prompt is artistically
good, factually correct, safe, or accepted by a target model.

## ZIP packages

A ZIP may contain the files above at its root or in one top-level folder. The loader finds the
shallowest `SKILL.md`, reads the package without extraction, and applies the same path and size
checks.

## Limits

- 512 KiB per included text file
- 2 MiB total included text
- 64 reference files
- no binary references, symlinks, code execution, imports, or package installation

These limits are security and usability boundaries, not a guarantee that every local model can
fit the resulting context.

## Creating a Skill with Codex

Give Codex documentation you have permission to use and ask it to create an independently
written Skill package containing `SKILL.md`, minimal references, an optional output contract,
tests, and explicit provenance. Review the generated files and run:

```powershell
local-prompt-studio --skill path\to\skill --inspect-skill
```

Do not ask Codex to copy third-party documentation into a public Skill unless its license
clearly permits redistribution.
