# Contributing

Thanks for considering a contribution. The project is dual-skill: software
engineering *and* civil/structural/architectural engineering. Both kinds of
contribution are welcome and equally important.

## Ground rules

- Open an issue before non-trivial work, so we can sanity-check the approach.
- Keep PRs focused. One change = one PR. Big PRs get rebased.
- All Python must pass `ruff` and `mypy --strict`. All TS must pass
  `eslint` + `tsc --noEmit`.
- Public functions/classes need docstrings and (where it adds value) examples.
- New behaviour needs tests. New compliance rules need *both* a unit test for
  the rule and a manifest+sample for end-to-end.

## Setup

```bash
# One-off
cp .env.example .env
make bootstrap

# Per session
make up
make logs           # in another shell

# Run tests
make test
make lint
```

## Code style

- Python: PEP 8 via `ruff format` (100-col).
- TypeScript: Prettier (100-col, single quotes, trailing commas).
- Names match the domain: `Standard`, `StandardClause`, `ComplianceFinding`,
  not `Doc`, `Chunk`, `Result`.
- Comments explain *why*, not *what*. The code says what.

## Contributing a new compliance rule

1. Identify the clause (e.g. QCVN 06:2022, điều 3.3.5).
2. Add a `Rule` subclass in `apps/api/src/tcvn_copilot/domain/compliance/rules.py`.
3. Append it to `RULES`.
4. Add unit tests in `apps/api/tests/unit/test_rules.py` covering at least
   one positive (compliant) and one negative (non-compliant) case.
5. (Optional but encouraged) provide a sample drawing JSON in
   `apps/api/tests/fixtures/` for integration tests.

## Contributing a new standard

See [docs/standards.md](docs/standards.md). The short version:

1. Drop the raw file under `packages/standards-corpus/raw/<CODE>/`.
2. Add a manifest YAML.
3. Run `make corpus-validate`.

The actual PDF is **not** committed (copyright); only the manifest is.

## Commit messages

We use Conventional Commits:

```
feat(api): add hybrid retrieval for QCVN 06 corpus
fix(worker): handle missing fire_rated field in egress data
docs(adr): record decision to use pgvector
chore(ci): bump gitleaks-action to v2.3
```

## Releasing

Maintainers only. Tag `vX.Y.Z` on `main` — the `release.yml` workflow
builds and pushes container images to GHCR with provenance + SBOM.
