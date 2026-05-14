# Security policy

## Reporting a vulnerability

If you discover a security issue, **do not open a public GitHub issue**.

Instead, email `security@tcvn-copilot.dev` (replace with your actual contact)
with:

- A description of the issue and its impact.
- Steps to reproduce or a proof-of-concept.
- Any mitigations you've already identified.

You'll receive an acknowledgement within 2 business days. We aim to ship
a fix within 30 days for high-severity issues, 90 days for medium.

## Scope

In scope:

- The API service (`apps/api`), worker, web app (`apps/web`).
- Container images published to GHCR under this repository.
- Default Helm/Kustomize manifests in `infra/`.

Out of scope:

- Issues that require physical access to the host.
- Denial-of-service via large file uploads when configured to bypass the
  `_MAX_BYTES` cap in `apps/api/src/tcvn_copilot/api/routes/uploads.py`.
- Issues in third-party services (Anthropic, AWS, etc.).

## Hardening notes

- Containers run as non-root (uid 1000/1001), read-only rootfs, no
  privileges, all capabilities dropped, seccomp `RuntimeDefault`.
- Argon2id password hashing.
- Short-lived (60-min) access tokens, longer-lived refresh tokens.
- Baseline security headers via middleware: `nosniff`, `DENY`,
  `strict-origin-when-cross-origin`, restrictive `Permissions-Policy`, HSTS.
- CORS is opt-in; `API_CORS_ORIGINS` is empty by default.
- Secrets never read directly from `os.environ`; all go through
  `pydantic-settings` and are typed `SecretStr`.

## CI gates

- `gitleaks` secret scan on every push.
- `pip-audit` and `pnpm audit` weekly + on every PR.
- `trivy fs` for filesystem CVE scan.
- CodeQL for Python + JavaScript.
- All Dependabot security updates auto-PR'd.

## Standards corpus

TCVN/QCVN texts are **never** committed to this repository. The manifest
captures metadata only. Operators are responsible for licensing the source
PDFs from the Ministry of Construction.
