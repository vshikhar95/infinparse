# Contributing

Thanks for helping. These parsers handle people's bank statements and purchase histories, so one rule comes first:

**Never commit, attach or paste a real statement or export, not even a redacted one.** That applies to fixtures,
issues, pull requests and screenshots.

## Adding or fixing a parser

1. Look at your file's structure with `python -m indian_finance_parsers.peek FILE` (needs the `excel` extra). It
   prints the layout with personal data masked. If the masking hides labels you need, or the file is a PDF, use
   [`tools/anonymise.py`](docs/anonymiser.md) instead: it keeps wording and swaps personal data for fakes.
2. Write a small synthetic fixture with that structure and **invented** values: shops like `TESTMART`, card numbers
   starting `4111`, account numbers of zeros, round amounts, dates far from today. Don't reuse real issue prices,
   published rates, fund or product names, branch codes, cities or timestamps (see the fixture checklist in
   `packages/indian-finance-parsers/docs/writing-an-adapter.md`).
3. Add a test, and a runbook from `docs/sources/_template.md` in the package you're changing.
4. Run the checks CI runs:

   ```bash
   uv sync
   uv run pytest -q -W error
   uvx ruff check .
   scripts/pii_check.sh
   ```

Parsers must stay pure: read only the file they are given; no network, environment variables or config files. Error
messages name the file, row and field, never amounts or descriptions.

## Pull requests

Use a short conventional title (`fix(hdfc_card): …`, `feat(steam): …`); merged PR titles become release notes.
Changes to `.github/`, `scripts/`, `.gitleaks*` and test fixtures need a maintainer's review (CODEOWNERS).

## Releases (maintainers)

Push a tag `<package>-v<version>` on a commit that is on `main`, for example `indian-finance-parsers-v0.1.1`. CI builds,
tests and publishes that package to PyPI and writes the GitHub release. See `docs/ci-cd.md`.
Releases go through a PR, never a direct push to `main`. History rewrites are logged in `docs/history-rewrites.md`.

Versions follow [Semantic Versioning](https://semver.org), shifted one place while a package is below 1.0, so that a
`>=0.1,<0.2` pin gets every safe update and never a breaking one:

| Change | Below 1.0 | From 1.0 |
|---|---|---|
| Breaking (renamed or removed function, field or behaviour) | bump minor: 0.1.4 → 0.2.0 | bump major: 1.3.0 → 2.0.0 |
| New feature, backwards compatible | bump patch: 0.1.0 → 0.1.1 | bump minor: 1.0.0 → 1.1.0 |
| Bug fix | bump patch: 0.1.1 → 0.1.2 | bump patch: 1.1.0 → 1.1.1 |

Each package is versioned on its own. 1.0 comes once the interface has settled (a release cycle without breaking
changes after the first real consumer has switched over).
