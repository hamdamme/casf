# Trusted checkpoint starts and complete bundle verification

SPEC §§15 and 19 require incremental verification from a trusted checkpoint
and a public verify-bundle operation. The current verifier always starts at
genesis; callers of open_bundle must remember to consume records to EOF.
This decision adds explicit interfaces without changing the version 1 bundle
format or weakening default full verification.

`VerificationAnchor(checkpoint, receipt, expected_checkpoint_hash=...)` owns
immutable evidence. The expected hash must come from independently retained or
provisioned trust, never be selected automatically from an untrusted bundle.
Construction checks encoding, schemas, digests and pair binding. Verification
still authenticates both signatures against the accepted manifest and witness
pin before consuming a suffix. Authority status and terminal revocation remain
required. An anchor is historical; it is not proof of witness freshness.

`verify(..., anchor=anchor)` consumes only records after the anchor count and
checkpoint/receipt extensions after its index. It starts record linkage at the
anchored head and both evidence chains at their pinned digests. It reports
absolute verified_from/verified_through for bodies actually checked, or 0/0
when none were checked. The assumptions identify the trusted prefix and state
that its bodies were not signature-checked. Record budgets count supplied
suffix records; checkpoint budgets count supplied extensions. State retained
before the anchor cannot be related without additional history and yields
INCONCLUSIVE. Conflicting or newer retained state still prevents acceptance.

In anchored/online modes, a final checkpoint cannot be extended by records or
checkpoints. Integrity mode with a final start rejects further records.
In anchored/online modes, every supplied receipt must match its checkpoint's index, count, head and digest. These shared
checks apply to full and incremental verification. Unknown trust, incomplete
evidence and unavailable fresh views never become PASS. Existing failure
precedence and explicit allow_unwitnessed policy remain in effect.

`verify_bundle(source, pins, ..., anchor=None)` opens a bounded standard bundle,
verifies it, drains records through EOF even after an early verdict, and closes
all files before returning. Late parse, count, resource or I/O failures raise;
no partial report is returned. Bundle metadata uses the same strict schema as
typed export results, including integer counts and protocol timestamps. It does not write retained state, retrieve
intermediate evidence or import writer/storage/signing code. Online verification
uses the existing caller-supplied validated-view callback. This adjusts the
SPEC section 19 names to the established `TrustPins`, `Report` and
`online_query` contracts instead of adding a second witness-client interface.
The pure verifier module remains the public import location.

With an explicit anchor, the bundle remains a full prefix from sequence 1.
The wrapper parses and counts its earlier records but skips their cryptographic
checks. Earlier checkpoint/receipt objects must be structurally consistent;
their signatures are not rechecked. Supplied evidence at the anchor must match
the explicit anchor. Full verification remains available by omitting it. A
bundle ending before the trusted count cannot pass. A separate suffix bundle
format is not introduced. Reports disclose the unexamined prefix; PASS does
not authenticate those earlier record bodies in this invocation.

The CLI retains full verification and durable state handling; no new shortcut
is enabled by default. This completes the remaining planned verifier API work,
subject to review and the later adversarial, research and release gates. Exact
validation belongs to the PR; historical outputs remain unchanged.

Affected requirements: R03, R07, R08, R10, R11.
