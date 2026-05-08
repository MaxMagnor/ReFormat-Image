from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageColor, ImageOps, UnidentifiedImageError

from .formats import ImageFormat, ensure_required_codec_available, format_from_extension, required_output_format


class ConversionError(RuntimeError):
    """Raised when an image cannot be converted."""


@dataclass(frozen=True)
class ConversionResult:
    source_path: Path
    output_path: Path
    warnings: tuple[str, ...]


def next_available_output_path(source_path: Path, target_format: ImageFormat) -> Path:
    base = source_path.with_suffix(target_format.primary_extension)
    if not base.exists():
        return base

    index = 1
    while True:
        candidate = source_path.with_name(f"{source_path.stem} ({index}){target_format.primary_extension}")
        if not candidate.exists():
            return candidate
        index += 1


def parse_background_color(value: str) -> tuple[int, int, int]:
    try:
        color = ImageColor.getrgb(value)
    except ValueError as exc:
        raise ConversionError(f"Invalid background color '{value}'. Use a value like #FFFFFF.") from exc
    if len(color) == 4:
        return color[:3]
    return color


def convert_image(
    source: str | Path,
    to_format: str,
    *,
    quality: int = 90,
    background: str = "#FFFFFF",
) -> ConversionResult:
    if not 1 <= quality <= 100:
        raise ConversionError("Quality must be between 1 and 100.")

    source_path = Path(source).expanduser()
    if not source_path.exists():
        raise ConversionError(f"File not found: {source_path}")
    if not source_path.is_file():
        raise ConversionError(f"Not a file: {source_path}")

    target_format = _target_format(to_format)
    ensure_required_codec_available(target_format)

    source_format = format_from_extension(source_path)
    if source_format is None:
        raise ConversionError(f"Unsupported input format: {source_path.suffix or '(none)'}")

    output_path = next_available_output_path(source_path, target_format)
    warnings: list[str] = []

    try:
        with Image.open(source_path) as opened:
            if _is_animated(opened):
                raise ConversionError("Animated images are not supported yet.")

            image = ImageOps.exif_transpose(opened)
            save_kwargs = _metadata_kwargs(opened, target_format)
            converted = _prepare_image(image, target_format, background, warnings)
            _add_quality_kwargs(save_kwargs, target_format, quality)

            if target_format.lossy:
                warnings.append(f"{target_format.label} output may use lossy compression.")
            warnings.append("Some metadata may not be preserved.")

            try:
                converted.save(output_path, target_format.pillow_format, **save_kwargs)
            except OSError as exc:
                raise ConversionError(f"Could not save {target_format.label}: {exc}") from exc
    except UnidentifiedImageError as exc:
        raise ConversionError(f"Could not read image file: {source_path}") from exc
    except OSError as exc:
        raise ConversionError(f"Could not open image file: {exc}") from exc

    return ConversionResult(source_path=source_path, output_path=output_path, warnings=tuple(dict.fromkeys(warnings)))


def _target_format(to_format: str) -> ImageFormat:
    try:
        return required_output_format(to_format)
    except ValueError as exc:
        raise ConversionError(str(exc)) from exc


def _is_animated(image: Image.Image) -> bool:
    return bool(getattr(image, "is_animated", False) or getattr(image, "n_frames", 1) > 1)


def _has_transparency(image: Image.Image) -> bool:
    if image.mode in {"RGBA", "LA"}:
        alpha = image.getchannel("A")
        return alpha.getextrema()[0] < 255
    if image.mode == "P" and "transparency" in image.info:
        return True
    return False


def _prepare_image(
    image: Image.Image,
    target_format: ImageFormat,
    background: str,
    warnings: list[str],
) -> Image.Image:
    if target_format.key == "jpg":
        if _has_transparency(image):
            warnings.append("Transparency was flattened onto the selected background color for JPG output.")
        return _flatten_to_rgb(image, parse_background_color(background))

    if target_format.key == "bmp" and image.mode not in {"RGB", "RGBA"}:
        return image.convert("RGB")

    if image.mode == "P" and target_format.key not in {"gif", "png"}:
        return image.convert("RGBA" if _has_transparency(image) else "RGB")

    return image.copy()


def _flatten_to_rgb(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    rgba = image.convert("RGBA")
    canvas = Image.new("RGBA", rgba.size, background + (255,))
    canvas.alpha_composite(rgba)
    return canvas.convert("RGB")


def _metadata_kwargs(source_image: Image.Image, target_format: ImageFormat) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    icc_profile = source_image.info.get("icc_profile")
    if icc_profile and target_format.key in {"jpg", "png", "webp", "tiff"}:
        kwargs["icc_profile"] = icc_profile

    exif = source_image.info.get("exif")
    if exif and target_format.key in {"jpg", "webp", "tiff"}:
        kwargs["exif"] = exif

    return kwargs


def _add_quality_kwargs(save_kwargs: dict[str, object], target_format: ImageFormat, quality: int) -> None:
    if target_format.key in {"jpg", "webp"}:
        save_kwargs["quality"] = quality
    if target_format.key == "jpg":
        save_kwargs["optimize"] = True
