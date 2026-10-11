"""Stable exception hierarchy for CASF.

Public errors are machine-distinguishable and carry safe messages only
(SPEC §8, §19). Never include secrets, payloads, or keys in messages.
"""

class CasfError(Exception):
    """Base class for all CASF errors."""

class SchemaError(CasfError):
    """Input violates the CASF data profile or a fixed object schema."""

class DuplicateKeyError(SchemaError):
    """An object contains a duplicate property name."""

class NumericError(SchemaError):
    """Forbidden or ambiguous numeric token (float, exponent, -0, unsafe int)."""

class UnicodeError_(SchemaError):
    """Invalid Unicode: lone surrogates or unencodable strings."""

class LimitError(CasfError):
    """A size, depth, or count bound was exceeded."""
