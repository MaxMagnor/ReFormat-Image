from __future__ import annotations

import json
from pathlib import Path

import pytest

from reformat_image.settings import (
    DEFAULT_SETTINGS,
    Settings,
    SettingsError,
    load_settings,
    reset_settings,
    save_settings,
    update_setting,
)


def test_load_settings_returns_defaults_when_missing(tmp_path: Path) -> None:
    assert load_settings(tmp_path / "missing.json") == DEFAULT_SETTINGS


def test_save_and_load_settings(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(overwrite_existing=True, jpg_quality=75)

    save_settings(settings, path)

    assert load_settings(path) == settings


def test_load_settings_ignores_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"overwrite_existing": True, "unknown": 123}), encoding="utf-8")

    assert load_settings(path).overwrite_existing is True


def test_update_setting_parses_bool_and_int() -> None:
    settings = update_setting(DEFAULT_SETTINGS, "overwrite_existing=true")
    settings = update_setting(settings, "jpg_quality=80")

    assert settings.overwrite_existing is True
    assert settings.jpg_quality == 80


def test_update_setting_rejects_invalid_key() -> None:
    with pytest.raises(SettingsError, match="Unknown setting"):
        update_setting(DEFAULT_SETTINGS, "bad=true")


def test_update_setting_rejects_invalid_quality() -> None:
    with pytest.raises(SettingsError, match="between 1 and 100"):
        update_setting(DEFAULT_SETTINGS, "webp_quality=200")


def test_reset_settings_writes_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    save_settings(Settings(overwrite_existing=True), path)

    reset_settings(path)

    assert load_settings(path) == DEFAULT_SETTINGS
