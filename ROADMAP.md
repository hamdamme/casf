# Roadmap

Phase plan for CASF. The source of truth is CASF SPEC 001: milestones
and effort estimates in §24, task definitions in §27. This file only
groups that work into phases and working sessions and tracks status.
One session means one focused working sitting.

| Phase | Scope (SPEC ref) | Tasks | Sessions | Status |
|---|---|---|---|---|
| 0. Documentation baseline | M0 | C00: source reconciliation, blocking decisions D01 to D05 | 1 | Done |
| 1. Protocol core review | M1 | Finish C02/C03: independent vector cross check, freeze casf-v1 vectors | 1 | Done (vectors frozen and cross checked, conformance suite wired, schema fix landed) |
| 2. Pure verifier | M2 | C04: offline and anchored verification, public key only | 1 to 2 | Done (integrity and anchored modes, enum report, 60 tests green) |
| 3. Writer and storage | M3 | C05: transactional SQLite append, idempotency, crash recovery | 2 | Done (append, idempotency, T06 concurrency, all T07 kill points, triggers, backup, startup checks, 83 tests green) |
| 4. Export and recovery | M4 | C06: evidence bundles, backup, restore drill | 1 | Not started |
| 5. Witness service | M5 | C07: durable acceptance state machine, receipts, HTTP | 2 | Not started |
| 6. Online verification | M5/M6 | C08: nonce freshness queries, checkpoint worker | 2 | Not started |
| 7. Lifecycle and CLI | M6 | C09: sealing, epoch rotation, revocation; C10: CLI hardening and packaging | 2 | Not started |
| 8. Research evaluation | M7 | C11: benchmarks, attack harnesses, RQ1 to RQ4 analysis | 2 | Not started |
| 9. Release candidate | M8 | C12: traceability audit, clean install, release checklist | 1 | Not started |

Total: 10 phases, about 15 to 17 sessions, matching the 12 to 21 week
part time estimate in SPEC §24. The milestone order is mandatory
(SPEC §24). Phases 5 and 6 carry the most design risk.

Status is updated at the end of each session. A phase is complete only
when its evidence is checked into the repository and its SPEC exit
criteria are satisfied.
