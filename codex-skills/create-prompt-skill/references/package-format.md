# Local Prompt Studio package format

Create this layout, omitting files that have no purpose:

```text
model-prompt-writer/
├── SKILL.md
├── skill.json
├── contract.json
├── provenance.json
├── references/
│   └── syntax.md
└── fixtures/
    ├── request.txt
    ├── expected-output.txt
    └── invalid-output.txt
```

## SKILL.md

Use YAML frontmatter with exactly `name` and `description`. In the body, define the transformation
workflow, priority of user constraints, reference syntax, output-only requirement, and handling of
unknowns. Keep detailed provider-specific syntax in one-level-deep references.

## skill.json

Use the Local Prompt Studio manifest:

```json
{
  "name": "Human-readable prompt writer name",
  "entrypoint": "SKILL.md",
  "include": ["references/syntax.md"],
  "contract": "contract.json"
}
```

Every included path must be relative, remain inside the package, and use `.md`, `.txt`, `.json`,
`.yaml`, or `.yml`. Do not include fixtures as model context unless they are essential examples.

## contract.json

Available keys are:

```json
{
  "name": "Contract name and version",
  "required_sections": ["section_one", "section_two"],
  "min_output_chars": 120,
  "max_output_chars": 2400,
  "forbidden_substrings": ["```"],
  "reference_pattern": "@image_(\\d+)",
  "reference_index_base": 0,
  "require_all_attachments_referenced": false,
  "tag_lists": {
    "ascii_only": true,
    "reject_duplicates": true,
    "reject_cross_section_duplicates": true,
    "sections": [
      {"section": "Positive Prompt", "min_tags": 12, "max_tags": 90},
      {"section": "Negative Prompt", "min_tags": 4}
    ]
  }
}
```

Section headings are case-insensitive and end with a colon. Required section order is enforced.
The reference regex needs one capture group containing the numeric index. Omit constraints that
cannot be checked deterministically.

For comma-delimited tag dialects, `tag_lists` can validate ASCII, normalized duplicates, tag
counts, literal required tags, and a minimum number of tags from a fixed baseline. Its configured
sections must also appear in `required_sections`. Do not add a free-form regex to express
model-specific semantics; contracts intentionally support only bounded declarative checks.

## provenance.json

Record evidence without loading it into prompt context:

```json
{
  "target_model": "provider/model-version",
  "created_at": "YYYY-MM-DD",
  "created_with": "Codex and human review",
  "sources": [
    {
      "title": "Source title",
      "location": "https://example.com/docs",
      "retrieved_at": "YYYY-MM-DD",
      "license": "license name or unknown",
      "redistribution_note": "Independent summary; no copied documentation"
    }
  ]
}
```

Use `unknown` instead of inventing license terms. A publicly readable page is not automatically
licensed for redistribution.

## Verification

From the Local Prompt Studio repository:

```powershell
local-prompt-studio --skill path\to\model-prompt-writer --inspect-skill
local-prompt-studio --skill path\to\model-prompt-writer `
  --validate-only path\to\model-prompt-writer\fixtures\expected-output.txt
```

Inspect output must identify the expected files and report `scripts_executed` as `false`. Validate
the invalid fixture too and expect a nonzero exit code.
