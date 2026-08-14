# Compatibility reports

Compatibility reports record real OpenAI-compatible server runs with synthetic data. They are
transport and workflow evidence, not model-quality benchmarks or endorsements of model artifacts.

## Verified reports

| Date | Server | Platform | Mode | Continuation | Contract | Evidence |
| --- | --- | --- | --- | ---: | ---: | --- |
| 2026-08-13 | LM Studio | Windows, Python 3.14.3 | Text, streamed | Triggered and recovered | Pass | [JSON report](../compatibility/reports/lm-studio-windows-2026-08-13.json) · [output fixture](../compatibility/fixtures/lm-studio-windows-2026-08-13-output.txt) |

The LM Studio run used the bundled model-neutral storyboard Skill and `examples/idea.txt`. The
first completion spent its 1,200-token budget in reasoning and returned no final content. Local
Prompt Studio preserved that reasoning, continued the same assistant turn, produced a 2,068
character result, and passed the four-section contract. `--no-save` prevented a history record.

## Report requirements

A report must include:

- project commit, date, operating system, Python version, and server build;
- a neutral API model identifier plus enough model-family information to interpret behavior;
- the exact synthetic fixture, non-secret generation settings, and whether images were used;
- exit status, validation result, continuation behavior, and relevant limitations;
- confirmation that no private prompt, history, credential, media, or model artifact is published.

Do not publish a local model path or artifact name when it contains unrelated personal or unsafe
labels. State that omission and do not describe the report as a reproducible model-quality result.
The repository never redistributes or endorses the tested model artifact.

## Submit a report

Open an issue before adding a new server or capability. Run with `--no-save`, use a repository
fixture, and include the output as reviewable text only when its content is ordinary and safe. Add
the output-contract command to CI so future changes continue to validate the recorded evidence.
