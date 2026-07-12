import os
import re
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_YAML = _ROOT / "config.yaml"
_CONFIG_EXAMPLE = _ROOT / "config.yaml.example"

_ENV_PREFIX = "ANKIETER_"


class Section(dict):
    """Dict z dostępem atrybutowym: section.key == section["key"]."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def get(self, key, default=None):
        return super().get(key, default)


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def _apply_env_override(data: dict, prefix: str = _ENV_PREFIX) -> dict:
    """Nadpisuje wartości z YAML danymi z env vars (ANKIETER_*)."""
    for key, val in data.items():
        env_key = prefix + key.upper()
        if isinstance(val, dict):
            _apply_env_override(val, prefix=f"{env_key}_")
        else:
            env_val = os.environ.get(env_key)
            if env_val is not None:
                data[key] = _coerce(env_val, val)
    return data


def _coerce(env_val: str, reference):
    """Konwertuje string z env na typ zgodny z defaultową wartością."""
    if isinstance(reference, bool):
        return env_val.lower() in ("true", "1", "yes")
    if isinstance(reference, int):
        return int(env_val)
    if isinstance(reference, float):
        return float(env_val)
    if isinstance(reference, list):
        return [item.strip() for item in env_val.split(",")]
    return env_val


def _load_config() -> Section:
    path = _CONFIG_YAML if _CONFIG_YAML.exists() else _CONFIG_EXAMPLE
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    _apply_env_override(raw)
    return {k: Section(v) if isinstance(v, dict) else v for k, v in raw.items()}


config = Section(_load_config())
