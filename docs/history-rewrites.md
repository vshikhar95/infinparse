# History rewrites

## 2026-10-24

`main` was force-pushed. Commits b7842c5 and 600c991 were replaced by c939768 (the Blinkit parser, squashed).

Why: those commits were pushed straight to `main` without a PR and failed the PII gate (app build numbers in the exporter read as long digit runs) and gitleaks (a synthetic test card in a fixture). No personal data was involved.

The tag `purchase-history-parsers-v0.1.1` was moved to the new commit. The files on PyPI are unchanged, because `exporters/` and `tests/` are not in the sdist or wheel.
