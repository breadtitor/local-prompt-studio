# Security model

Local Prompt Studio treats both the selected Skill and the inference server as trust decisions
made by the user.

## Protected assets

- User prompt ideas and attached images
- Optional endpoint credentials
- Local generation history
- Integrity of the host filesystem

## Boundaries

| Component | Trust level | Behavior |
| --- | --- | --- |
| Local Prompt Studio core | Trusted installed code | Loads bounded text, sends requests, validates, saves history |
| User-selected Skill | Untrusted data | Included in model context; never executed |
| Inference endpoint | User-selected service | Receives system text, user text, and attached image bytes |
| Generated output | Untrusted text | Displayed and saved; never executed automatically |

The default endpoint is `http://127.0.0.1:1234/v1`, but the CLI and UI allow a remote URL.
Choosing a remote URL changes the privacy boundary: all supplied text and image bytes are sent
to that server.

## Loader defenses

- Package paths must stay relative and cannot contain parent traversal.
- ZIP packages are read without extraction, avoiding overwrite-on-extract behavior.
- Only allow-listed text suffixes can enter model context.
- Per-file, aggregate-size, and file-count bounds reduce accidental context flooding.
- A manifest cannot request a program, hook, or dependency installation.

## History behavior

History is stored under the user's application-data directory unless overridden. Records contain
the raw request, generated text, validation report, non-secret settings, and attachment
basenames. Image content is not copied. The environment variable's name may be recorded; its
secret value is not.

Use `--no-save` for sensitive one-off prompts. Directory permissions and backups remain the
user's responsibility.

## Out of scope

- Detecting every malicious instruction inside natural-language Skill text
- Guaranteeing the safety or licensing of model output
- Securing a remote inference operator
- Sandboxing the local model server itself
- Circumventing a model provider's safeguards or terms
