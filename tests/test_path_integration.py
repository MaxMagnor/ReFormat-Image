from __future__ import annotations

from reformat_image.path_integration import _split_path


def test_split_path_discards_empty_segments() -> None:
    assert _split_path(r"C:\One;;C:\Two") == [r"C:\One", r"C:\Two"]
