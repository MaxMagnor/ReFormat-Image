from __future__ import annotations

from pathlib import Path

from PIL import Image

from reformat_image.cli import main


def test_cli_set_prints_settings_help(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert main(["--set", "overwrite_existing=true"]) == 0

    output = capsys.readouterr().out
    assert "overwrite_existing = True" in output
    assert "Settings file:" in output


def test_cli_settings_prints_human_help(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert main(["--settings"]) == 0

    output = capsys.readouterr().out
    assert "Available settings:" in output
    assert "overwrite_existing" in output
    assert "--set name=value" in output


def test_cli_accepts_multiple_set_flags(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert main(["--set", "overwrite_existing=true", "--set", "jpg_quality=91"]) == 0

    output = capsys.readouterr().out
    assert "overwrite_existing = True" in output
    assert "jpg_quality = 91" in output


def test_cli_hides_conversion_warnings_by_default(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    source = tmp_path / "image.png"
    Image.new("RGB", (2, 2), "red").save(source)

    assert main(["--convert", str(source), "--to", "jpg"]) == 0

    output = capsys.readouterr().out
    assert "Saved:" in output
    assert "metadata" not in output.lower()


def test_cli_can_show_conversion_warnings(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    source = tmp_path / "image.png"
    Image.new("RGB", (2, 2), "red").save(source)

    assert main(["--convert", str(source), "--to", "jpg", "--show-warnings", "--quiet"]) == 0

    output = capsys.readouterr().err
    assert "metadata" in output.lower()
