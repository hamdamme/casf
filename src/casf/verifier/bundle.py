"""Bounded public bundle verification with complete input consumption."""

from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

from casf.bundle import BundleReadError, open_bundle
from casf.canonical.limits import MAX_CHECKPOINT_CHAIN_STEPS, MAX_JSONL_LINE_BYTES
from casf.model.operations import Checkpoint, WitnessResult
from casf.types import JsonObject
from casf.verifier.anchor import VerificationAnchor
from casf.verifier.report import AnchorStatus, Mode, Report, Result, TrustPins


def _extensions(evidence: Iterable[JsonObject], anchor: VerificationAnchor,
                *, receipts: bool = False) -> Iterator[JsonObject]:
    """Skip bounded historical evidence, checking its encoding and ordering."""
    field = 'checkpoint_index' if receipts else 'index'
    expected = anchor.receipt if receipts else anchor.checkpoint.to_dict()
    start_index = anchor.checkpoint.index
    start_body = anchor.checkpoint.body
    previous = -1
    extension_started = False
    for envelope in evidence:
        body = envelope.get('body')
        index = body.get(field) if isinstance(body, dict) else None
        if type(index) is not int:
            raise BundleReadError('evidence checkpoint index must be an integer')
        if index > start_index:
            extension_started = True
            yield envelope  # The core verifier reports invalid extension evidence.
            continue
        if extension_started or index <= previous:
            raise BundleReadError('historical evidence is not ordered by checkpoint index')
        previous = index
        value = WitnessResult(envelope) if receipts else Checkpoint(envelope)
        if (value.log_id != start_body['log_id']
                or value.body['manifest_hash'] != start_body['manifest_hash']):
            raise BundleReadError('historical evidence belongs to a different log or manifest')
        if index == start_index and envelope != expected:
            raise BundleReadError('bundle evidence conflicts with the explicit anchor')


def verify_bundle(source: str | Path, pins: TrustPins, mode: Mode = Mode.INTEGRITY,
                  *, anchor: VerificationAnchor | None = None,
                  allow_unwitnessed: bool = False,
                  online_query: Callable[[], Any] | None = None,
                  retained_checkpoint: tuple[int, str] | None = None,
                  retained_revoked: bool = False,
                  max_chain_steps: int = MAX_CHECKPOINT_CHAIN_STEPS,
                  max_records: int = 1_000_000,
                  max_line_bytes: int = MAX_JSONL_LINE_BYTES,
                  max_evidence_objects: int = 100_000,
                  max_total_bytes: int = 256 * 1024 * 1024) -> Report:
    """Verify a standard bundle, drain through EOF, and close before returning.

    Parse, count, resource and I/O errors raise even after an early verdict.
    With an explicit anchor, earlier record bodies are parsed but their
    signatures are not checked. max_records limits the entire bundle, including
    that prefix. No retained state is written; online_query must return an
    already validated fresh witness view. Omitting anchor verifies from genesis.
    """
    from casf.verifier import verify

    with open_bundle(source, max_line_bytes=max_line_bytes, max_records=max_records,
                     max_evidence_objects=max_evidence_objects,
                     max_total_bytes=max_total_bytes) as bundle:
        records: Iterable[JsonObject] = bundle.records
        checkpoints: Iterable[JsonObject] = bundle.checkpoints
        receipts: Iterable[JsonObject] = bundle.receipts
        if anchor is not None:
            # enumerate uses the reader's checked full-prefix sequence, never
            # untrusted count fields to choose the cryptographic boundary.
            start_count = anchor.checkpoint.count
            records = (record for seq, record in enumerate(bundle.records, 1)
                       if seq > start_count)
            checkpoints = _extensions(bundle.checkpoints, anchor)
            receipts = _extensions(bundle.receipts, anchor, receipts=True)
        report = verify(
            bundle.manifest, records, pins, mode, checkpoint_envelopes=checkpoints,
            receipt_envelopes=receipts, status_envelopes=bundle.statuses,
            allow_unwitnessed=allow_unwitnessed, online_query=online_query,
            retained_checkpoint=retained_checkpoint, retained_revoked=retained_revoked,
            max_chain_steps=max_chain_steps, max_records=max_records, anchor=anchor)
        # Early failure, unknown trust, or a budget verdict must not conceal
        # a malformed tail or metadata/count mismatch.
        for _ in bundle.records:
            pass
        if anchor is not None:
            # Also finish structural checks when the core stopped early or
            # integrity mode intentionally skipped checkpoint authentication.
            for _ in checkpoints:
                pass
            for _ in receipts:
                pass
            through = bundle.metadata['through']
            assert isinstance(through, int)  # EOF has checked it against the observed count.
            if through < anchor.checkpoint.count:
                report.result = Result.FAIL
                report.anchor_status = AnchorStatus.INCOMPLETE
                report.checkpoint = None
                report.witnessed_through = report.unwitnessed_count = None
                if 'ANCHOR_INCOMPLETE' not in report.diagnostic_codes:
                    report.diagnostic_codes.append('ANCHOR_INCOMPLETE')
    return report
