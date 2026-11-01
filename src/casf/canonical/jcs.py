"""RFC 8785 JSON Canonicalization Scheme, restricted to the CASF data
profile (SPEC §9).

Profile rules beyond plain JCS:
  - values: strings, booleans, null, arrays, objects, safe integers only
  - floats are forbidden everywhere; wire tokens with '.', exponent, or
    negative zero are rejected even if integral
  - duplicate property names and invalid Unicode (lone surrogates) rejected
  - Python booleans never satisfy integer validation

JCS core rules implemented (RFC 8785 §3.2):
  - object properties sorted by UTF-16 code units (big-endian comparison)
  - minimal string escaping; non-ASCII emitted as raw UTF-8
  - no insignificant whitespace
"""

import json
import math

from casf.canonical.limits import SAFE_INT_MAX, SAFE_INT_MIN, Limits
from casf.errors import DuplicateKeyError, LimitError, NumericError, SchemaError, UnicodeError_
from casf.types import JsonValue

__all__ = ["canonicalize", "parse", "parse_config", "utf16_sort_key", "validate"]

# ---------------------------------------------------------------- JCS core

def utf16_sort_key(s: str) -> bytes:
    """JCS property ordering key: UTF-16 code units, big-endian."""
    try:
        return s.encode("utf-16-be")
    except UnicodeEncodeError as e:
        raise UnicodeError_("string contains invalid Unicode") from e

def _escape_string(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif o < 0x20:
            out.append(f"\\u{o:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)

def _serialize(value: JsonValue, depth: int, limits: Limits) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if type(value) is int:  # bool is a subclass; explicitly excluded above
        if not (SAFE_INT_MIN <= value <= SAFE_INT_MAX):
            raise NumericError("integer outside safe range")
        return str(value)
    if isinstance(value, str):
        encoded = _encode_utf8(value)
        if len(encoded) > limits.max_string_bytes:
            raise LimitError("string exceeds maximum UTF-8 byte length")
        return _escape_string(value)
    if isinstance(value, list):
        _check_depth(depth, limits)
        return "[" + ",".join(_serialize(v, depth + 1, limits) for v in value) + "]"
    if isinstance(value, dict):
        _check_depth(depth, limits)
        keys = list(value.keys())
        for k in keys:
            if not isinstance(k, str):
                raise SchemaError("object keys must be strings")
        keys.sort(key=utf16_sort_key)
        return "{" + ",".join(
            _escape_string(k) + ":" + _serialize(value[k], depth + 1, limits)
            for k in keys) + "}"
    raise SchemaError(f"unsupported value type: {type(value).__name__}")

def _check_depth(depth: int, limits: Limits) -> None:
    if depth > limits.max_depth:
        raise LimitError("nesting depth exceeds maximum")

def _encode_utf8(s: str) -> bytes:
    try:
        return s.encode("utf-8")
    except UnicodeEncodeError as e:
        raise UnicodeError_("string contains invalid Unicode") from e

def validate(value: JsonValue, limits: Limits | None = None) -> None:
    """Validate a Python value against the CASF data profile (no output)."""
    limits = limits or Limits()
    _serialize(value, 1, limits)  # body counts as depth 1 (SPEC §9)

def canonicalize(value: JsonValue, limits: Limits | None = None) -> bytes:
    """Validate and return the RFC 8785 canonical UTF-8 encoding."""
    limits = limits or Limits()
    text = _serialize(value, 1, limits)
    return text.encode("utf-8")

# ------------------------------------------------------- strict wire parser

def _reject_number_token(token: str) -> None:
    # Any float-routed token ('.', 'e', 'E', NaN, Infinity) is forbidden.
    raise NumericError(f"forbidden numeric token: {token!r}")

def _parse_int(token: str) -> int:
    if token.startswith("-0"):
        raise NumericError("negative zero is forbidden")
    value = int(token)
    if not (SAFE_INT_MIN <= value <= SAFE_INT_MAX):
        raise NumericError("integer outside safe range")
    return value

def _no_duplicates(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    obj: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in obj:
            raise DuplicateKeyError(f"duplicate property name: {key!r}")
        obj[key] = value
    return obj

def parse(text: str | bytes) -> JsonValue:
    """Parse wire JSON strictly: duplicate keys, floats, exponents, -0,
    NaN/Infinity, and invalid Unicode are rejected before any use."""
    if isinstance(text, bytes):
        if text.startswith(b"\xef\xbb\xbf"):
            raise SchemaError("byte order mark is forbidden")
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as e:
            raise SchemaError("input is not valid UTF-8") from e
    try:
        value: JsonValue = json.loads(
            text,
            object_pairs_hook=_no_duplicates,
            parse_int=_parse_int,
            parse_float=_reject_number_token,
            parse_constant=_reject_number_token,
        )
    except (DuplicateKeyError, NumericError):
        raise
    except json.JSONDecodeError as e:
        raise SchemaError(f"invalid JSON: {e.msg}") from e
    # reject lone surrogates surviving escapes (json accepts "\ud800")
    _check_strings(value, set())
    return value


def parse_config(text: str | bytes) -> object:
    """Parse bounded configuration JSON with strict names and numbers.

    Unlike authenticated CASF wire objects, configuration may contain finite
    decimal values such as a fractional timeout. Duplicate fields, unsafe
    integers, negative zero, nonfinite numbers, BOM, invalid UTF 8, and lone
    surrogates remain rejected.
    """
    if isinstance(text, bytes):
        if text.startswith(b"\xef\xbb\xbf"):
            raise SchemaError("byte order mark is forbidden")
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SchemaError("input is not valid UTF-8") from exc

    def parse_float(token: str) -> float:
        value = float(token)
        if not math.isfinite(value) or (value == 0.0 and token.startswith("-")):
            raise NumericError(f"forbidden numeric token: {token!r}")
        return value

    def no_duplicate_config(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateKeyError(f"duplicate property name: {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            text, object_pairs_hook=no_duplicate_config,
            parse_int=_parse_int, parse_float=parse_float,
            parse_constant=_reject_number_token)
    except (DuplicateKeyError, NumericError):
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise SchemaError("invalid configuration JSON") from exc

    def check(current: object, depth: int = 1) -> None:
        if depth > 16:
            raise SchemaError("configuration nesting limit exceeded")
        if isinstance(current, str):
            try:
                size = len(current.encode("utf-8"))
            except UnicodeEncodeError as exc:
                raise SchemaError("configuration contains invalid Unicode") from exc
            if size > 32768:
                raise SchemaError("configuration string exceeds its limit")
        elif isinstance(current, dict):
            for key, item in current.items():
                try:
                    size = len(key.encode("utf-8"))
                except UnicodeEncodeError as exc:
                    raise SchemaError("configuration contains invalid Unicode") from exc
                if size > 32768:
                    raise SchemaError("configuration key exceeds its limit")
                check(item, depth + 1)
        elif isinstance(current, list):
            for item in current:
                check(item, depth + 1)
    check(value)
    return value

def _check_strings(value: JsonValue, seen: set[int]) -> None:
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, str):
        _encode_utf8(value)  # raises UnicodeError_ on lone surrogates
    elif isinstance(value, dict):
        for k, v in value.items():
            _encode_utf8(k)
            _check_strings(v, seen)
    elif isinstance(value, list):
        for v in value:
            _check_strings(v, seen)
