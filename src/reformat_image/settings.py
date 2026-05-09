from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import ImageColor


APP_DIR_NAME = "ReFormat Image"
SETTINGS_FILE_NAME = "settings.json"


class SettingsError(RuntimeError):
    """Raised when settings cannot be read or written."""


@dataclass(frozen=True)
class Settings:
    overwrite_existing: bool = False
    delete_original_after_conversion: bool = False
    show_warnings: bool = False
    jpg_quality: int = 90
    webp_quality: int = 90
    webp_lossless: bool = False
    background_color: str = "#FFFFFF"
    preserve_metadata: bool = True


DEFAULT_SETTINGS = Settings()
SETTING_TYPES = {field: type(value) for field, value in asdict(DEFAULT_SETTINGS).items()}


def config_dir() -> Path:
    root = os.environ.get("APPDATA")
    if root:
        return Path(root) / APP_DIR_NAME
    return Path.home() / "AppData" / "Roaming" / APP_DIR_NAME


def config_path() -> Path:
    return config_dir() / SETTINGS_FILE_NAME


def load_settings(path: Path | None = None) -> Settings:
    settings_path = path or config_path()
    if not settings_path.exists():
        return DEFAULT_SETTINGS

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SettingsError(f"Could not read settings file: {exc}") from exc

    if not isinstance(raw, dict):
        raise SettingsError("Settings file must contain a JSON object.")

    values = asdict(DEFAULT_SETTINGS)
    for key, value in raw.items():
        if key not in values:
            continue
        values[key] = _coerce_value(key, value)
    return Settings(**values)


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    settings_path = path or config_path()
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise SettingsError(f"Could not save settings file: {exc}") from exc
    return settings_path


def reset_settings(path: Path | None = None) -> Path:
    return save_settings(DEFAULT_SETTINGS, path)


def update_setting(settings: Settings, assignment: str) -> Settings:
    if "=" not in assignment:
        raise SettingsError("Settings must use key=value syntax.")

    key, raw_value = assignment.split("=", 1)
    key = key.strip()
    if key not in SETTING_TYPES:
        valid = ", ".join(sorted(SETTING_TYPES))
        raise SettingsError(f"Unknown setting '{key}'. Valid settings: {valid}.")

    values = asdict(settings)
    values[key] = _coerce_value(key, raw_value.strip())
    return Settings(**values)


def settings_as_json(settings: Settings) -> str:
    return json.dumps(asdict(settings), indent=2)


def settings_help(settings: Settings) -> str:
    lines = [
        "ReFormat Image settings",
        "",
        f"Settings file: {config_path()}",
        "",
        "Change a setting:",
        "  ReFormatImage.exe --set name=value",
        "  reformat --set name=value",
        "",
        "Available settings:",
    ]
    descriptions = {
        "overwrite_existing": "Replace the target file if it already exists instead of creating image (1).png.",
        "delete_original_after_conversion": "Delete the original file after a successful conversion.",
        "show_warnings": "Show non-fatal warnings such as metadata loss and lossy output.",
        "jpg_quality": "Default JPG quality from 1 to 100.",
        "webp_quality": "Default lossy WebP quality from 1 to 100.",
        "webp_lossless": "Save WebP output as lossless when true.",
        "background_color": "Color used when flattening transparency to JPG, for example #FFFFFF.",
        "preserve_metadata": "Try to preserve ICC profile and EXIF data when the target format supports it.",
    }
    values = asdict(settings)
    for key, description in descriptions.items():
        lines.append(f"  {key} = {values[key]!r}")
        lines.append(f"    {description}")
    return "\n".join(lines)


def _coerce_value(key: str, value: Any) -> Any:
    expected = SETTING_TYPES[key]
    if expected is bool:
        return _coerce_bool(key, value)
    if expected is int:
        number = _coerce_int(key, value)
        if key.endswith("_quality") and not 1 <= number <= 100:
            raise SettingsError(f"{key} must be between 1 and 100.")
        return number
    if expected is str:
        text = str(value)
        if key == "background_color":
            try:
                ImageColor.getrgb(text)
            except ValueError as exc:
                raise SettingsError("background_color must be a valid color like #FFFFFF.") from exc
        return text
    return value


def _coerce_bool(key: str, value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise SettingsError(f"{key} must be true or false.")


def _coerce_int(key: str, value: Any) -> int:
    if isinstance(value, bool):
        raise SettingsError(f"{key} must be a number.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise SettingsError(f"{key} must be a number.") from exc
