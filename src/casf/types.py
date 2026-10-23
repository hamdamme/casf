"""Shared type aliases for the CASF restricted JSON data profile (SPEC §9).

The profile admits only: null, booleans, safe integers, strings, arrays,
and objects with string keys. Floats are forbidden everywhere.
"""

__all__ = ["JsonObject", "JsonValue"]

type JsonValue = None | bool | int | str | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]
