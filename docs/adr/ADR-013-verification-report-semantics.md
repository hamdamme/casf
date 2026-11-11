# Verification report semantics

This decision records its implementation-time context. Statements about separate
work refer to that stage; use the [current reference](../current-reference.md)
and [completion tracker](../release/completion-tracker.md) for present behavior
and acceptance status.

SPEC §15 fixes report enums and distinguishes unavailable evidence from proven
mismatches. The implementation currently uses older enum labels, reports
missing trust as FAIL, and initializes unchecked dimensions as successful.
ADR-011 deferred this conflict. This decision resolves report semantics before
the first stable release without changing authenticated formats or permitting
any new PASS outcome.

Diagnostic JSON advances to `report_version=2` because the enum values and
missing-evidence verdicts change. `overall` is the canonical verdict field;
`result` remains an identical compatibility field. Python `Report.overall`
reads the existing `result`. Existing Python enum member names remain aliases
where their meaning is unambiguous; serialized values use the SPEC labels.
The legacy `UNTRUSTED` member aliases `CONFLICT`; missing pins now use UNKNOWN.
The cryptographic profile and database schema remain version 1.

Missing authority/witness pins, missing applicable status or a sufficiently
recent active statement, and absent anchor/receipt evidence are INCONCLUSIVE.
Invalid schemas, signatures, identity bindings, retained-state conflicts and
revocation remain FAIL. A supplied history shorter than an authenticated
anchor remains FAIL/INCOMPLETE: the count mismatch is established. A missing
anchor cannot establish that mismatch. An unsupported positive integer version
is FAIL/UNSUPPORTED; malformed version fields are FAIL/INVALID. The existing strict policy on any supplied status below the serial minimum
remains non-PASS, even alongside a newer statement. Invalid input
cannot be hidden by a later missing-evidence observation or resource limit.

Unestablished witness coverage and unwitnessed counts are null.
Signature and chain dimensions start NOT_CHECKED and become VALID only after
their required traversal finishes; observed invalidity is never overwritten.
Protocol VALID describes checked structure, not completion of unexamined input.
Anchor status starts NONE in integrity mode and INCOMPLETE otherwise. Online
freshness starts INCONCLUSIVE until a view is checked. A PASS still requires
accepted independent trust and all predicates of the requested mode.

CLI exit categories remain specific: malformed profile/schema is 2,
unsupported profile or missing/revoked/conflicting trust is 3, other
inconclusive evidence is 4, and proven cryptographic or chain failures are 1.
Reports are retained for these outcomes. Writer startup, restore and checkpoint
state advancement still require PASS with trusted evidence. Authenticated
status/revocation observations remain separately retainable on non-PASS.

Tests cover the report enums and migration fields, absent evidence, malformed
and unsupported versions, failure precedence, unchecked dimensions, CLI exit
codes and retained-state behavior. Historical research outputs are preserved;
any affected reruns require new output locations. Incremental verification and
other public operation results remain separate acceptance work.

Affected requirements: R03, R07, R10.
