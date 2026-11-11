# Contributing

CASF is currently a solo maintained research project. Contributions are
welcome but please open an issue before large changes.

## Ground rules
- Read `docs/specification/` and `DEVELOPMENT.md` before editing.
- Preserve casf-v1 bytes, domains, trust rules, and failure semantics.
- Do not invent cryptography or silently relax validation.
- Synthetic data only; never commit keys, databases, or real audit data.
- Record affected protocol requirements (R01-R12) in the requirement evidence
  map or review record, with tests actually run. Keep commit subjects and PR
  descriptions short: explain the behavior change and relevant validation.
- Keep completion phases, sessions and personal task assignments in the
  completion tracker, not PR descriptions.

## Review
The maintainer reviews every change before merge, whatever its origin.
Security-critical changes are reviewed in this order: failing test
first, protocol rule second, implementation third.

## Documentation consistency

- Run `.venv/bin/python tests/repository_check.py` before submitting changes.
  It reads every tracked file, checks local Markdown links including headings,
  parses structured formats, restores SQL fixtures and checks retained hashes.
  Stage new intended files before running it locally. CI checks the committed tree.
  A structural pass is not a semantic review: also reconcile current claims,
  historical status and any affected examples against the implementation.

- Keep active installation, API and status guidance linked from
  `docs/current-reference.md`. Distinguish intended specification behavior
  from verified implementation behavior.
- Use `research/README.md` for canonical labels. Preserve original reports,
  raw results and historical labels; correct interpretations in current text.
- Identify the source revision and exact artifacts for each validation or
  approval. A later commit does not inherit an earlier artifact's checks.
- When the preprint changes, update its Word and PDF reading copies, inspect
  their rendering, refresh `SHA256SUMS.txt`, and pin its README retrieval
  instructions to a commit that actually contains those files.
