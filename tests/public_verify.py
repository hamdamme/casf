"""Verify synthetic public evidence in an isolated installed environment."""

import json
import sys
from pathlib import Path

from casf import crypto
from casf.verifier import Mode, Result, TrustPins, TrustStatus, VerificationAnchor, verify_bundle


def main():
    directory = Path(sys.argv[1])
    trust = json.loads(directory.with_name(directory.name + '-trust.json').read_text())
    authority = crypto.b64url_decode(trust['authority'])
    witness = crypto.b64url_decode(trust['witness'])
    pins = TrustPins(authority_keys={crypto.key_id(authority): authority},
                     witness_keys={crypto.key_id(witness): witness},
                     log_id=trust['log_id'], manifest_hash=trust['manifest_hash'])
    report = verify_bundle(directory, pins)
    assert report.result is Result.PASS
    assert report.trust_status is TrustStatus.TRUSTED
    assert report.verified_through == 2
    assert 'STATUS_CURRENTNESS_UNCONFIRMED' in report.diagnostic_codes
    checkpoint = json.loads((directory / 'checkpoints.jsonl').read_text())
    receipt = json.loads((directory / 'receipts.jsonl').read_text())
    anchor = VerificationAnchor(checkpoint, receipt,
                                expected_checkpoint_hash=trust['checkpoint_hash'])
    suffix = verify_bundle(directory, pins, Mode.ANCHORED, anchor=anchor, allow_unwitnessed=True)
    assert suffix.result is Result.PASS
    assert suffix.verified_from == suffix.verified_through == 2
    assert suffix.witnessed_through == suffix.unwitnessed_count == 1
    assert suffix.assumptions['prefix_signatures_checked'] is False
    forbidden = ('casf.writer', 'casf.storage', 'casf.witness', 'casf.cli', 'casf.keys')
    assert not any(name == prefix or name.startswith(prefix + '.')
                   for name in sys.modules for prefix in forbidden)
    assert not any(p.suffix in ('.db', '.key', '.pem') for p in directory.iterdir())
    print(json.dumps({'result': report.result.value, 'verified_through': report.verified_through,
                      'trust_status': report.trust_status.value,
                      'diagnostic_codes': report.diagnostic_codes}, sort_keys=True))


if __name__ == '__main__':
    main()
