from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType
from typing import TypeAlias, cast

TomlScalar: TypeAlias = str | int | float | bool | None
TomlValue: TypeAlias = TomlScalar | list["TomlValue"] | dict[str, "TomlValue"]
TomlTable: TypeAlias = dict[str, TomlValue]


def load_module_from_path(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {module_name}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _coerce_toml_value(value: object) -> TomlValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [_coerce_toml_value(item) for item in value]

    if isinstance(value, dict):
        table: TomlTable = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("Expected TOML table keys to be strings")
            table[key] = _coerce_toml_value(item)
        return table

    raise TypeError(f"Unsupported TOML value type: {type(value).__name__}")


def parse_toml_text(text: str) -> TomlTable:
    loaded = cast(object, tomllib.loads(text))
    if not isinstance(loaded, dict):
        raise TypeError("Expected TOML root to be a table")
    coerced = _coerce_toml_value(loaded)
    if not isinstance(coerced, dict):
        raise TypeError("Expected TOML root to remain a table")
    return coerced


def get_toml_table(table: TomlTable, key: str) -> TomlTable:
    value = table[key]
    if not isinstance(value, dict):
        raise AssertionError(f"Expected '{key}' to be a TOML table")
    return value
