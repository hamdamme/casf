# DEVELOPMENT.md — working agreements for this project

Read docs/specification/ and this file before editing. Implement only
the named CASF task and its prerequisites. Preserve casf-v1 bytes,
domains, trust rules and failure semantics. Do not invent cryptography,
silently relax validation, or claim tests that were not run. Add tests
for the requirement IDs named in the task. Use synthetic test keys.

If a specification conflict affects bytes, trust or durability, record
it as an ADR question before implementing that dependent behavior.

Finish with: changed files, tests actually run, results, limitations,
and the exact acceptance criteria still unmet. Do not publish a release.

Task register: CASF SPEC 001 §27 (C00-C12).
