from __future__ import annotations

from pathlib import Path

import pytest

from reformat_image import updater
from reformat_image.updater import ReleaseAsset, ReleaseInfo, UpdateError, create_replacement_helper, update_application


def test_update_application_rejects_source_run() -> None:
    with pytest.raises(UpdateError, match="packaged"):
        update_application(launch_helper=False)


def test_update_application_reports_current_when_no_newer_release(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(updater, "fetch_latest_release", lambda _url: ReleaseInfo("v1.1.0", ()))

    result = update_application(current_exe=tmp_path / "ReFormatImage.exe", launch_helper=False)

    assert result.update_available is False


def test_update_application_requires_exe_asset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(updater, "fetch_latest_release", lambda _url: ReleaseInfo("v1.2.0", ()))

    with pytest.raises(UpdateError, match="does not include"):
        update_application(current_exe=tmp_path / "ReFormatImage.exe", launch_helper=False)


def test_update_application_stages_newer_asset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    staged = tmp_path / "staged.exe"
    monkeypatch.setattr(
        updater,
        "fetch_latest_release",
        lambda _url: ReleaseInfo("v1.2.0", (ReleaseAsset("ReFormatImage.exe", "https://example.invalid/ReFormatImage.exe"),)),
    )
    monkeypatch.setattr(updater, "download_asset", lambda _url, _tag, _name="ReFormatImage.exe": staged)
    monkeypatch.setattr(updater, "create_replacement_helper", lambda _current, _staged: tmp_path / "helper.cmd")

    result = update_application(current_exe=tmp_path / "ReFormatImage.exe", launch_helper=False)

    assert result.update_available is True
    assert result.staged_path == staged
    assert result.staged_paths == (staged,)


def test_update_application_stages_optional_assets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_download(_url: str, _tag: str, name: str = "ReFormatImage.exe") -> Path:
        return tmp_path / name

    monkeypatch.setattr(
        updater,
        "fetch_latest_release",
        lambda _url: ReleaseInfo(
            "v1.2.0",
            (
                ReleaseAsset("ReFormatImage.exe", "https://example.invalid/ReFormatImage.exe"),
                ReleaseAsset("ReFormatImageContext.exe", "https://example.invalid/ReFormatImageContext.exe"),
                ReleaseAsset("reformat.exe", "https://example.invalid/reformat.exe"),
            ),
        ),
    )
    monkeypatch.setattr(updater, "download_asset", fake_download)
    monkeypatch.setattr(updater, "create_replacement_helper", lambda _current, _staged: tmp_path / "helper.cmd")

    result = update_application(current_exe=tmp_path / "ReFormatImage.exe", launch_helper=False)

    assert [path.name for path in result.staged_paths] == ["ReFormatImage.exe", "ReFormatImageContext.exe", "reformat.exe"]


def test_create_replacement_helper_contains_move_command(tmp_path: Path) -> None:
    current = tmp_path / "ReFormatImage.exe"
    staged = tmp_path / "updates" / "ReFormatImage.exe"
    staged.parent.mkdir()

    helper = create_replacement_helper(current, staged)

    assert "move /y" in helper.read_text(encoding="utf-8")
