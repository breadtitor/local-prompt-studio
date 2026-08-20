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
  "format_version": 1,
  "name": "Example Prompt Writer",
  "entrypoint": "SKILL.md",
  "include": ["references/output-format.md"],
  "contract": "contract.json",
  "provenance": {
    "license": "MIT",
    "source": "Independently authored example"
  }
}
```

All paths are relative to the package. Absolute paths and parent traversal (`..`) are rejected.
The manifest is an extension of Local Prompt Studio, not a claim of universal Skill-package
compatibility.

New shared packages should set `format_version` to `1` and include `provenance.license` plus
`provenance.source`. The loader keeps accepting legacy manifests without an explicit version as
version 1, but rejects unknown future versions instead of guessing. Machine-readable schemas are
published at [`schemas/skill.schema.json`](../schemas/skill.schema.json) and
[`schemas/contract.schema.json`](../schemas/contract.schema.json).

## Output contract

`contract.json` adds deterministic checks after generation:

```json
{
  "format_version": 1,
  "name": "Example contract v1",
  "required_sections": ["summary", "prompt", "constraints"],
  "min_output_chars": 120,
  "max_output_chars": 4000,
  "forbidden_substrings": ["```"],
  "reference_pattern": "@image_(\\d+)",
  "reference_index_base": 0,
  "require_all_attachments_referenced": true,
  "tag_lists": {
    "ascii_only": true,
    "reject_duplicates": true,
    "reject_cross_section_duplicates": true,
    "sections": [
      {
        "section": "Positive Prompt",
        "min_tags": 12,
        "max_tags": 90,
        "required_tags": ["masterpiece", "best quality"]
      },
      {
        "section": "Negative Prompt",
        "min_tags": 4,
        "minimum_required_tag_matches": {
          "tags": ["lowres", "bad anatomy", "watermark"],
          "count": 2
        }
      }
    ]
  }
}
```

Section names are matched as case-insensitive headings followed by a colon or as Markdown
headings. If
`required_sections` is supplied, their order is also checked. The reference regex must contain
one capture group for the numeric attachment index. Regular expressions are bounded to 256
characters. A contract may define at most 32 case-insensitive forbidden substrings; these remain
literal text rather than regular expressions so an untrusted Skill cannot add a costly pattern.

### Tag-list checks

`tag_lists` is optional and is intended for comma-delimited tag dialects. Every configured
`section` must also be in `required_sections`, so heading existence and order remain explicit.
For each listed section, the runner can check tag count bounds, literal required tags, or that a
minimum number of tags comes from a configured baseline. It can additionally reject non-ASCII
tags, duplicates within a list, and normalized duplicates between lists. For duplicate checks,
underscores and spaces are equivalent and a simple numeric weight suffix is ignored.

This remains an output-shape check. It does not verify whether a tag is supported by a checkpoint,
whether a target workflow is installed, or whether the result is artistically good or safe.
`tag_lists` has no user-supplied regular expressions, scripts, or network actions.

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
