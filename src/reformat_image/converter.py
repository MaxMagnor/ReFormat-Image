from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

from PIL import Image, ImageColor, ImageOps, UnidentifiedImageError

from .formats import ImageFormat, ensure_required_codec_available, format_from_extension, required_output_format


class ConversionError(RuntimeError):
    """Raised when an image cannot be converted."""


@dataclass(frozen=True)
class ConversionResult:
    source_path: Path
    output_path: Path
    warnings: tuple[str, ...]
    deleted_original: bool = False


def next_available_output_path(source_path: Path, target_format: ImageFormat, *, overwrite_existing: bool = False) -> Path:
    base = source_path.with_suffix(target_format.primary_extension)
    if overwrite_existing:
        return base
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
    quality: int | None = None,
    jpg_quality: int = 90,
    webp_quality: int = 90,
    webp_lossless: bool = False,
    background: str = "#FFFFFF",
    overwrite_existing: bool = False,
    delete_original_after_conversion: bool = False,
    preserve_metadata: bool = True,
) -> ConversionResult:
    for label, value in {"quality": quality, "jpg_quality": jpg_quality, "webp_quality": webp_quality}.items():
        if value is not None and not 1 <= value <= 100:
            raise ConversionError(f"{label} must be between 1 and 100.")

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

    output_path = next_available_output_path(source_path, target_format, overwrite_existing=overwrite_existing)
    if _same_path(source_path, output_path):
        raise ConversionError("Source and output path are the same. In-place conversion is not supported.")

    warnings: list[str] = []

    try:
        with Image.open(source_path) as opened:
            if _is_animated(opened):
                raise ConversionError("Animated images are not supported yet.")

            image = ImageOps.exif_transpose(opened)
            save_kwargs = _metadata_kwargs(opened, target_format) if preserve_metadata else {}
            converted = _prepare_image(image, target_format, background, warnings)
            _add_quality_kwargs(
                save_kwargs,
                target_format,
                quality=_quality_for_format(target_format, quality, jpg_quality, webp_quality),
                webp_lossless=webp_lossless,
            )

            if target_format.lossy:
                warnings.append(f"{target_format.label} output may use lossy compression.")
            if preserve_metadata:
                warnings.append("Some metadata may not be preserved.")

            try:
                _save_image(converted, output_path, target_format, overwrite_existing=overwrite_existing, save_kwargs=save_kwargs)
            except OSError as exc:
                raise ConversionError(f"Could not save {target_format.label}: {exc}") from exc
    except UnidentifiedImageError as exc:
        raise ConversionError(f"Could not read image file: {source_path}") from exc
    except OSError as exc:
        raise ConversionError(f"Could not open image file: {exc}") from exc

    deleted_original = False
    if delete_original_after_conversion:
        if not output_path.exists():
            raise ConversionError("Converted file was not created; original file was preserved.")
        try:
            source_path.unlink()
            deleted_original = True
        except OSError as exc:
            raise ConversionError(f"Converted file was created, but the original could not be deleted: {exc}") from exc

    return ConversionResult(
        source_path=source_path,
        output_path=output_path,
        warnings=tuple(dict.fromkeys(warnings)),
        deleted_original=deleted_original,
    )


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

    if target_format.key in {"gif", "ico"} and image.mode not in {"RGB", "RGBA", "P"}:
        return image.convert("RGBA")

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


def _add_quality_kwargs(save_kwargs: dict[str, object], target_format: ImageFormat, *, quality: int, webp_lossless: bool) -> None:
    if target_format.key == "webp" and webp_lossless:
        save_kwargs["lossless"] = True
    if target_format.key in {"jpg", "webp"} and not (target_format.key == "webp" and webp_lossless):
        save_kwargs["quality"] = quality
    if target_format.key == "jpg":
        save_kwargs["optimize"] = True


def _quality_for_format(target_format: ImageFormat, quality: int | None, jpg_quality: int, webp_quality: int) -> int:
    if quality is not None:
        return quality
    if target_format.key == "webp":
        return webp_quality
    return jpg_quality


def _save_image(
    image: Image.Image,
    output_path: Path,
    target_format: ImageFormat,
    *,
    overwrite_existing: bool,
    save_kwargs: dict[str, object],
) -> None:
    if target_format.key == "ico":
        save_kwargs.setdefault("sizes", [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    if not overwrite_existing:
        image.save(output_path, target_format.pillow_format, **save_kwargs)
        return

    fd, temp_name = tempfile.mkstemp(prefix=f".{output_path.stem}.", suffix=output_path.suffix, dir=output_path.parent)
    os.close(fd)
    Path(temp_name).unlink(missing_ok=True)
    temp_path = Path(temp_name)
    try:
        image.save(temp_path, target_format.pillow_format, **save_kwargs)
        temp_path.replace(output_path)
    finally:
        temp_path.unlink(missing_ok=True)


def _same_path(left: Path, right: Path) -> bool:
    return left.resolve().as_posix().casefold() == right.resolve().as_posix().casefold()
