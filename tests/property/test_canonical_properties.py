"""R01/R10: generated serialization, ordering, ambiguity and size boundaries."""

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from casf.canonical.jcs import canonicalize, parse
from casf.canonical.limits import Limits
from casf.errors import DuplicateKeyError, LimitError, NumericError, UnicodeError_
from tests.property.strategies import objects, profile, text, values


@profile
@given(values)
def test_canonical_roundtrip_preserves_generated_values(value):
    encoded = canonicalize(value)
    assert parse(encoded) == value
    assert canonicalize(parse(encoded)) == encoded
    # A separate JSON implementation must interpret the bytes identically.
    assert json.loads(encoded) == value


@profile
@given(objects)
def test_object_permutation_preserves_canonical_bytes(value):
    reverse = dict(reversed(list(value.items())))
    encoded = canonicalize(value)
    assert canonicalize(reverse) == encoded
    assert list(json.loads(encoded)) == sorted(value, key=lambda key: key.encode('utf-16-be'))


@profile
@given(text, values, values)
def test_escaped_duplicate_names_are_rejected(key, first, second):
    # Literal and escaped spellings can name the same Unicode property.
    literal = json.dumps(key, ensure_ascii=False).encode()
    escaped = json.dumps(key, ensure_ascii=True).encode()
    raw = b'{' + literal + b':' + canonicalize(first) + b',' + escaped + b':' + canonicalize(second) + b'}'
    with pytest.raises(DuplicateKeyError):
        parse(raw)


@profile
@given(st.integers(0, 15), st.sampled_from(['.', 'e', 'E']))
def test_integer_looking_noninteger_tokens_are_rejected(number, separator):
    with pytest.raises(NumericError):
        parse(str(number) + separator + '0')


@profile
@given(st.integers(0xD800, 0xDFFF))
def test_lone_surrogates_fail_in_names_and_values(codepoint):
    escaped = f'"\\u{codepoint:04x}"'
    for raw in (escaped, '{' + escaped + ':null}'):
        with pytest.raises(UnicodeError_):
            parse(raw)


@profile
@given(st.integers(1, 16), st.sampled_from(['array', 'object']))
def test_container_depth_has_an_exact_boundary(depth, kind):
    value = None
    for _ in range(depth):
        value = [value] if kind == 'array' else {'a': value}
    assert parse(canonicalize(value, Limits(max_depth=depth))) == value
    with pytest.raises(LimitError):
        canonicalize(value, Limits(max_depth=depth - 1))


@profile
@given(st.integers(1, 64), st.sampled_from(['a', 'é', '😀']), st.booleans())
def test_utf8_byte_limit_applies_to_names_and_values(length, character, as_key):
    value = character * length
    size = len(value.encode())
    body = {value: None} if as_key else value
    assert parse(canonicalize(body, Limits(max_string_bytes=size))) == body
    with pytest.raises(LimitError):
        canonicalize(body, Limits(max_string_bytes=size - 1))
