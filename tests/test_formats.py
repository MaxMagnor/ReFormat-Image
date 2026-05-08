from __future__ import annotations

import pytest

from reformat_image.formats import required_output_format


def test_required_output_format_aliases() -> None:
    assert required_output_format("jpg").key == "jpg"
    assert required_output_format("jpeg").key == "jpg"
    assert required_output_format("tif").key == "tiff"
    assert required_output_format(".PNG").key == "png"


def test_required_output_format_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported output format"):
        required_output_format("pdf")
