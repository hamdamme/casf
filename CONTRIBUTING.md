# Contributing

CASF is currently a solo maintained research project. Contributions are
welcome but please open an issue before large changes.

## Ground rules
- Read `docs/specification/` and `DEVELOPMENT.md` before editing.
- Preserve casf-v1 bytes, domains, trust rules, and failure semantics.
- Do not invent cryptography or silently relax validation.
- Synthetic data only; never commit keys, databases, or real audit data.
- Every change must state which requirement IDs (R01-R12) it affects
  and which tests were actually run.

## Review
The maintainer reviews every change before merge, whatever its origin.
Security-critical changes are reviewed in this order: failing test
first, protocol rule second, implementation third.
