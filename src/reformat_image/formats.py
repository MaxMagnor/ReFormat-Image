from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, features


@dataclass(frozen=True)
class ImageFormat:
    key: str
    label: str
    pillow_format: str
    extensions: tuple[str, ...]
    lossy: bool = False
    optional: bool = False

    @property
    def primary_extension(self) -> str:
        return self.extensions[0]


REQUIRED_FORMATS: dict[str, ImageFormat] = {
    "png": ImageFormat("png", "PNG", "PNG", (".png",)),
    "jpg": ImageFormat("jpg", "JPG", "JPEG", (".jpg", ".jpeg"), lossy=True),
    "webp": ImageFormat("webp", "WebP", "WEBP", (".webp",), lossy=True),
    "bmp": ImageFormat("bmp", "BMP", "BMP", (".bmp",)),
    "tiff": ImageFormat("tiff", "TIFF", "TIFF", (".tiff", ".tif")),
    "gif": ImageFormat("gif", "GIF", "GIF", (".gif",)),
    "ico": ImageFormat("ico", "ICO", "ICO", (".ico",)),
}

ALIASES: dict[str, str] = {
    "jpeg": "jpg",
    "jpe": "jpg",
    "tif": "tiff",
}

OPTIONAL_FORMATS: dict[str, ImageFormat] = {
    "avif": ImageFormat("avif", "AVIF", "AVIF", (".avif",), lossy=True, optional=True),
    "heif": ImageFormat("heif", "HEIF", "HEIF", (".heif", ".heic"), optional=True),
}

REQUIRED_CONTEXT_MENU_TARGETS = ("png", "jpg", "webp", "bmp", "tiff", "gif", "ico")


def normalize_format_name(value: str) -> str:
    normalized = value.strip().lower().lstrip(".")
    return ALIASES.get(normalized, normalized)


def required_output_format(value: str) -> ImageFormat:
    key = normalize_format_name(value)
    try:
        return REQUIRED_FORMATS[key]
    except KeyError as exc:
        supported = ", ".join(sorted(REQUIRED_FORMATS))
        raise ValueError(f"Unsupported output format '{value}'. Supported formats: {supported}.") from exc


def format_from_extension(path: Path) -> ImageFormat | None:
    suffix = path.suffix.lower()
    for image_format in available_input_formats().values():
        if suffix in image_format.extensions:
            return image_format
    return None


def available_input_formats() -> dict[str, ImageFormat]:
    result = dict(REQUIRED_FORMATS)
    for key, image_format in OPTIONAL_FORMATS.items():
        if is_pillow_format_available(image_format):
            result[key] = image_format
    return result


def is_pillow_format_available(image_format: ImageFormat) -> bool:
    if image_format.key == "webp":
        return bool(features.check("webp"))
    if image_format.key == "avif":
        return bool(features.check("avif"))
    if image_format.key == "heif":
        registered = Image.registered_extensions()
        return any(registered.get(extension) == "HEIF" for extension in image_format.extensions)
    if image_format.key in {"ico", "gif"}:
        registered = Image.registered_extensions()
        return any(extension in registered for extension in image_format.extensions)
    return True


def ensure_required_codec_available(image_format: ImageFormat) -> None:
    if image_format.key == "webp" and not features.check("webp"):
        raise ValueError("This Pillow installation does not include WebP support.")
