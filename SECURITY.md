# Security policy

## Supported versions

Until the first stable release, security fixes are made on the latest `main` branch and the
most recent release.

## Reporting a vulnerability

Please do not publish exploit details in a public issue. Use GitHub's private vulnerability
reporting feature for this repository. Include the affected version, reproduction steps,
impact, and any suggested mitigation. Expect an initial acknowledgment within seven days.

Do not include real API keys, private prompts, personal history records, or sensitive images in
a report. Use minimal synthetic data.

## Security invariants

- A Skill is untrusted text and is never executed as code.
- ZIP Skills are read in place and are not extracted.
- Relative paths cannot escape the selected Skill package.
- Included text has per-file, total-size, and file-count limits.
- The default inference endpoint is the local loopback interface.
- Secrets are read only from an explicitly named environment variable and are not saved to
  history.

Changes that weaken an invariant require an explicit security review and documentation update.
