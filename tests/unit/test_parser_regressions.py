"""R01/R10: minimized findings from generated input and parser corpus checks."""

import pytest

from casf.canonical.jcs import canonicalize, parse, parse_config
from casf.canonical.limits import MAX_STRING_BYTES, Limits
from casf.errors import DuplicateKeyError, LimitError, NumericError


def test_object_key_limit_matches_string_value_limit():
    with pytest.raises(LimitError):
        canonicalize({'a': None}, Limits(max_string_bytes=0))
    with pytest.raises(LimitError):
        canonicalize({'a' * (MAX_STRING_BYTES + 1): None})


@pytest.mark.parametrize('parser', [parse, parse_config])
def test_long_integer_has_a_stable_numeric_error(parser):
    # One digit above CPython's default conversion ceiling; do not rely on
    # that interpreter setting to enforce CASF's much smaller safe range.
    with pytest.raises(NumericError):
        parser('9' * 4301)


def test_deep_wire_input_has_a_stable_limit_error():
    with pytest.raises(LimitError):
        parse('[' * 2048 + '0' + ']' * 2048)


@pytest.mark.parametrize('parser', [parse, parse_config])
def test_duplicate_name_diagnostic_does_not_echo_private_input(parser):
    marker = 'synthetic-secret-marker'
    with pytest.raises(DuplicateKeyError) as caught:
        parser('{"' + marker + '":0,"' + marker + '":1}')
    assert marker not in str(caught.value)
