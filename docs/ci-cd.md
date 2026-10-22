# CI/CD

Decided 2026-10-22, after a security review and an expert panel (packaging, Actions security, privacy, why-auditor,
prior-art). This file says what runs and why; the workflows in `.github/workflows/` are the implementation.

## Context

- `infinparse` is a public uv workspace with two independently released packages, `indian-finance-parsers` and
  `purchase-history-parsers`. It also holds browser userscripts (`exporters/*.user.js`) and a bash PII gate
  (`scripts/pii_check.sh`).
- There is one maintainer. Outside contributors send fork PRs.
- The libraries parse personal financial files. Fixtures are synthetic, and real-file parity is checked only
  locally, in the maintainer's private repo.
- Commits pass the maintainer's local hook (gitleaks, regexes, and a local model reading the diff) before they leave
  the machine. Nothing in CI can run that model.

## Goals

1. Every PR and push proves four things: tests pass on the oldest and newest supported Python, both packages build
   with exactly the intended files, the code is linted, and no personal data or secret is in the tree, the history,
   or the PR text.
2. Releasing is one action: pushing a tag. Everything after it is automatic, with no stored PyPI token.
3. Breakage from new upstream releases (pdfplumber, pandas, casparser) is caught weekly.
4. A fork PR can't read secrets, publish, or weaken the gates it is judged by.

## CI: `ci.yml` (push to `main`, and every pull request)

| Job | Runs | Why |
|---|---|---|
| `test` | Python 3.11 and 3.14: `uv sync --locked`, then `pytest -q -W error` | the supported range's floor and ceiling; the lockfile makes red mean "our change" |
| `test-lowest` | 3.11: `uv sync --resolution lowest-direct`, then pytest (without `-W error`) | proves the finance package's version floors are real |
| `build` | `uv build` for each package; checks sdist and wheel members against an allowlist; installs the finance wheel with no extras, imports every PDF-only adapter, and asserts that `pandas` is absent | only intended files ship; the extras stay optional |
| `lint` | `ruff check` (defaults + bugbear), Biome on the exporters, shellcheck on `scripts/`, actionlint and zizmor on the workflows | consistent feedback; the gate and the workflows are code too |
| `pii` | `scripts/pii_check.sh` over the tree, full history and merge commits, plus PR title and body. On PRs the script comes from `main`, not the PR | home paths, family words, binaries, unscannable names |
| `secrets` | the pinned gitleaks binary with the committed `.gitleaks.toml`, over the tree and history | secrets, card numbers, and Indian identifiers: PAN, Aadhaar (spaced or not), IFSC, UPI, mobiles, masked cards |
| `dependency-review` | PRs only | flags a PR whose `uv.lock` change adds a known-vulnerable package |
| `audit` | `uv audit --locked` (OSV), with the uv version pinned because the command is experimental | known CVEs in the locked set |

CodeQL runs through GitHub's **default setup** (enabled in settings; no workflow file) for Python and JavaScript. It
catches regex-backtracking (ReDoS) bugs, among others.

**Weekly (`weekly.yml`):** `uv lock --upgrade`, then the tests and `uv audit`, against the newest dependencies. That is
goal 3. If it fails, GitHub emails the maintainer; no issue bot. **Dependabot:** GitHub Actions pins weekly, plus `uv`
security updates to `uv.lock`.

Tests that support these goals:
- every parser package imports no network module (`socket`, `urllib`, `http`, `requests`);
- every exporter header keeps `@grant none`, has no `@connect`, and matches only its own store;
- exporters save only the history rows, with no `<script>`, no account email and no profile link, behind a
  "personal data" banner;
- parser exceptions carry the file, row and field, never descriptions or amounts;
- one canary PDF test: a synthetic PDF generated at test time (fpdf2, dev-only) and parsed end to end. It catches
  pdfplumber API drift, not layout changes in real bank PDFs.

## CD: `release.yml` (pushing a tag `<package>-v<version>`)

The **version comes from the tag** (hatch-vcs, matched per package), so there are no version-bump commits. A tag
pushed by the maintainer triggers workflows normally. Tags made with `GITHUB_TOKEN` would not, which is why
release-please was dropped.

1. **`build`** (read-only token, no publishing rights): check out the tag; confirm the tagged commit is on `main`;
   test; `uv build --package <name>` from a clean checkout; check the members against the allowlist; upload `dist/`
   as an artifact.
2. **`publish`** (environment `pypi-<package>`, `id-token: write` only, no checkout and no third-party code beyond the pinned
   publish action): download the artifact and upload it with PyPI Trusted Publishing.
3. **`github-release`** (`contents: write`): generate the notes from the merged PRs since that package's previous tag,
   run them through the PII gate, then create the GitHub release with `dist/` attached. The notes never reach PyPI
   (its page shows the README), so checking them after the upload is enough.

PyPI's trusted-publisher entries name this repo, `release.yml` and the package's own environment (`pypi-<package>`;
PyPI rejects two publishers with the same repo, workflow and environment). For the first release they
are "pending publishers". The `pypi-<package>` environments have no reviewer, because a solo maintainer can't approve their own
run. Two things gate publishing instead: the tag ruleset (only the maintainer can create `*-v*` tags) and the
environment's deployment rule (tags only, from this repo).

## Hardening

- Every action is pinned to a full commit SHA, choosing the newest release at least 14 days old; Dependabot bumps
  the pins with a 14-day cooldown. The gitleaks and actionlint binaries are verified against pinned checksums.
- Workflows default to `permissions: contents: read`. Only the jobs that need more get it: `id-token: write` for
  publish, `contents: write` for creating the release.
- Workflows trigger on `pull_request`, never `pull_request_target`. No `${{ }}` user text is interpolated into
  `run:` (PR titles go through `env:`), and checkouts use `persist-credentials: false`.
- CODEOWNERS covers `.github/`, `scripts/`, `.gitleaks*`, and `**/fixtures/**`.
- Contributors get CONTRIBUTING.md (fixtures must be invented), a PR template, issue templates ("never attach a
  statement or export; paste `peek` output"), and SECURITY.md.

## Maintainer checklist (one-time, on GitHub and PyPI)

1. Push first to a **private** repo. Run `scripts/pii_check.sh <private denylist>`, then make the repo public.
2. Branch ruleset on `main`: PRs required, the CI jobs required, no force-push or deletion. Tag ruleset on `*-v*`:
   only you may create, update or delete.
3. Environments `pypi-indian-finance-parsers` and `pypi-purchase-history-parsers`: deployment allowed from `*-v*`
   tags only.
4. Actions settings: allow GitHub-owned actions plus the pinned third-party ones; require approval for outside
   contributors' workflow runs; default token read-only.
5. Turn on secret scanning and push protection, Dependabot alerts, private vulnerability reporting, and CodeQL
   default setup.
6. PyPI: add a pending trusted publisher for each package (this repo, `release.yml`, environment `pypi-<package>`). Use a
   hardware-key 2FA on GitHub and PyPI.

## Not doing

- **release-please.** It needs a GitHub App token for its PRs and tags to trigger CI, plus a careful bootstrap. A tag
  push is one action with less machinery.
- **Type checking and pylint.** Lightly annotated code; ruff covers most of pylint's rules.
- **A formatter check, coverage thresholds.** Churn without defect value.
- **The middle Python versions (3.12, 3.13) in CI.** Pure Python; the floor and ceiling bracket them.
- **OpenSSF Scorecard.** Revisit after the first release.
