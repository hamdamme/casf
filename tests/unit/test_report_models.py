"""Report enums and compatibility names have one canonical representation."""

import pytest

from casf.verifier.report import AnchorStatus, Dimension, ProtocolStatus, TrustStatus


@pytest.mark.parametrize('enum,values', [
    (ProtocolStatus, {'VALID', 'INVALID', 'UNSUPPORTED'}),
    (Dimension, {'VALID', 'INVALID', 'NOT_CHECKED'}),
    (TrustStatus, {'TRUSTED', 'UNKNOWN', 'REVOKED', 'CONFLICT'}),
    (AnchorStatus, {'NONE', 'MATCHED', 'PARTIAL_ANCHOR', 'INCOMPLETE', 'DIVERGENT'}),
])
def test_report_enums_match_spec(enum, values):
    assert {member.value for member in enum} == values


def test_legacy_member_names_are_aliases_of_canonical_values():
    assert Dimension.OK is Dimension.VALID
    assert Dimension.FAIL is Dimension.INVALID
    assert TrustStatus.OK is TrustStatus.TRUSTED
    assert TrustStatus.UNTRUSTED is TrustStatus.CONFLICT
    assert AnchorStatus.OK is AnchorStatus.MATCHED
    assert AnchorStatus.NOT_REQUESTED is AnchorStatus.NONE
