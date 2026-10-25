"""T01/T02 (SPEC §21): strict parsing and canonical byte exactness."""

import pytest

from casf.canonical.jcs import canonicalize, parse
from casf.errors import DuplicateKeyError, LimitError, NumericError, SchemaError, UnicodeError_

# ---------------- T01: reject before signing/verification ----------------

def test_reject_duplicate_keys():
    with pytest.raises(DuplicateKeyError):
        parse('{"a":1,"a":2}')

def test_reject_float():
    with pytest.raises(NumericError):
        parse('{"x":1.5}')
    with pytest.raises(NumericError):
        parse('{"x":1e3}')     # exponent integer
    with pytest.raises(NumericError):
        parse('{"x":1E3}')
    with pytest.raises(NumericError):
        parse('{"x":-0}')      # negative zero
    with pytest.raises(NumericError):
        parse('{"x":NaN}')
    with pytest.raises(NumericError):
        parse('{"x":Infinity}')

def test_reject_unsafe_integer():
    with pytest.raises(NumericError):
        parse('{"x":9007199254740992}')            # 2^53
    with pytest.raises(NumericError):
        parse('{"x":-9007199254740992}')
    assert parse('{"x":9007199254740991}')["x"] == 9007199254740991  # 2^53-1 ok

def test_reject_invalid_unicode():
    with pytest.raises(UnicodeError_):
        parse('{"\ud800":"x"}')        # lone surrogate via escape
    with pytest.raises(SchemaError):
        parse(b"\xef\xbb\xbf{}")    # BOM
    with pytest.raises(SchemaError):
        parse(b'{"x":"\xff"}')          # invalid UTF-8 bytes

def test_reject_unknown_field_at_parse_is_app_level():
    # parsers keep arbitrary application keys in payload/attributes;
    # fixed protocol bodies reject them at schema validation (see test_schema)
    assert parse('{"payload":{"anything":true}}') == {"payload": {"anything": True}}

def test_bool_is_not_int():
    from casf.model import schema
    with pytest.raises(SchemaError):
        schema.validate_body({"version": True}, {"version": schema.K("int")}, "t")

# ---------------- T02: exact canonical bytes ----------------

def test_key_ordering_utf16_not_codepoint():
    # U+1F600 (surrogate pair D83D DE00) sorts BEFORE U+FFFF in UTF-16
    # order, but AFTER in code-point order. JCS requires UTF-16 order.
    obj = {"\uffff": 1, "\U0001F600": 2}
    assert canonicalize(obj) == '{"\U0001F600":2,"\uffff":1}'.encode()

def test_key_ordering_basic():
    assert canonicalize({"b": 1, "a": 2}) == b'{"a":2,"b":1}'

def test_string_escaping_controls():
    obj = {"s": "\u0000\u001f\u007f\t\n\r\b\f"}
    assert canonicalize(obj) == b'{"s":"\\u0000\\u001f\x7f\\t\\n\\r\\b\\f"}'


def test_non_ascii_passthrough():
    s = "héllo € 中文 \U0001F600"
    assert canonicalize({"s": s}) == ('{"s":"' + s + '"}').encode("utf-8")

def test_depth_and_string_limits():
    with pytest.raises(LimitError):
        canonicalize(eval("[" * 18 + "1" + "]" * 18))  # 18 levels, exceeds max 16
    from casf.canonical.limits import Limits
    with pytest.raises(LimitError):
        canonicalize({"s": "x" * 40000}, Limits(max_string_bytes=32768))

def test_nested_arrays_and_safe_edges():
    obj = {"a": [[1, -9007199254740991], [9007199254740991, None, True, False]]}
    out = canonicalize(obj)
    assert out == b'{"a":[[1,-9007199254740991],[9007199254740991,null,true,false]]}'

def test_canonicalize_rejects_nonstring_keys():
    with pytest.raises(SchemaError):
        canonicalize({1: "x"})
