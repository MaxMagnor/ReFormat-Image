from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, features

from reformat_image.converter import ConversionError, convert_image, next_available_output_path
from reformat_image.formats import REQUIRED_FORMATS


def test_next_available_output_path_uses_numbered_suffix(tmp_path: Path) -> None:
    source = tmp_path / "image.webp"
    source.write_bytes(b"placeholder")
    (tmp_path / "image.png").write_bytes(b"existing")
    (tmp_path / "image (1).png").write_bytes(b"existing")

    assert next_available_output_path(source, REQUIRED_FORMATS["png"]) == tmp_path / "image (2).png"


def test_next_available_output_path_can_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "image.webp"
    source.write_bytes(b"placeholder")
    target = tmp_path / "image.png"
    target.write_bytes(b"existing")

    assert next_available_output_path(source, REQUIRED_FORMATS["png"], overwrite_existing=True) == target


def test_convert_transparent_png_to_jpg_flattens_to_white(tmp_path: Path) -> None:
    source = tmp_path / "transparent.png"
    image = Image.new("RGBA", (2, 2), (255, 0, 0, 0))
    image.putpixel((0, 0), (0, 0, 255, 255))
    image.save(source)

    result = convert_image(source, "jpg", quality=90)

    output = Image.open(result.output_path)
    assert output.mode == "RGB"
    flattened_pixel = output.getpixel((1, 1))
    assert all(channel >= 240 for channel in flattened_pixel)
    assert any("Transparency was flattened" in warning for warning in result.warnings)


def test_convert_rejects_animated_gif(tmp_path: Path) -> None:
    source = tmp_path / "animated.gif"
    first = Image.new("RGB", (2, 2), "red")
    second = Image.new("RGB", (2, 2), "blue")
    first.save(source, save_all=True, append_images=[second], duration=50, loop=0)

    with pytest.raises(ConversionError, match="Animated images are not supported yet"):
        convert_image(source, "png")


def test_convert_rejects_unsupported_input_extension(tmp_path: Path) -> None:
    source = tmp_path / "image.txt"
    source.write_text("not an image")

    with pytest.raises(ConversionError, match="Unsupported input format"):
        convert_image(source, "png")


def test_convert_rejects_unknown_output_format(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    Image.new("RGB", (2, 2), "red").save(source)

    with pytest.raises(ConversionError, match="Unsupported output format"):
        convert_image(source, "pdf")


def test_convert_overwrites_existing_target_when_enabled(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    target = tmp_path / "image.jpg"
    Image.new("RGB", (2, 2), "red").save(source)
    Image.new("RGB", (2, 2), "blue").save(target)

    result = convert_image(source, "jpg", overwrite_existing=True)

    assert result.output_path == target
    assert target.exists()
    assert source.exists()


def test_convert_deletes_original_after_success(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    Image.new("RGB", (2, 2), "red").save(source)

    result = convert_image(source, "bmp", delete_original_after_conversion=True)

    assert result.output_path.exists()
    assert not source.exists()
    assert result.deleted_original is True


def test_convert_rejects_same_source_and_target(tmp_path: Path) -> None:
    source = tmp_path / "image.png"
    Image.new("RGB", (2, 2), "red").save(source)

    with pytest.raises(ConversionError, match="In-place conversion is not supported"):
        convert_image(source, "png", overwrite_existing=True)


@pytest.mark.parametrize(
    ("target", "extension"),
    [
        ("png", ".png"),
        ("jpg", ".jpg"),
        ("bmp", ".bmp"),
        ("tiff", ".tiff"),
        ("gif", ".gif"),
        ("ico", ".ico"),
    ],
)
def test_basic_required_conversions(tmp_path: Path, target: str, extension: str) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (4, 4), "green").save(source)

    result = convert_image(source, target)

    assert result.output_path.suffix == extension
    assert result.output_path.exists()


@pytest.mark.skipif(not features.check("webp"), reason="Pillow was built without WebP support")
def test_basic_webp_conversion(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (4, 4), "green").save(source)

    result = convert_image(source, "webp")

    assert result.output_path.suffix == ".webp"
    assert result.output_path.exists()
