# ReFormat Image

ReFormat Image is a small Windows utility that adds image format conversion to the classic right-click context menu. It is intended for quick conversions such as WebP to PNG or JPG without opening a full image editor.

Explorer only launches the external executable. Image libraries are not loaded into Explorer.

## Supported Formats

Required input and output formats:

- PNG
- JPG / JPEG
- WebP
- BMP
- TIFF / TIF

Optional formats such as AVIF, HEIC/HEIF, ICO, and GIF may be added later when codec support is practical and reliable. Animated images are not supported in v1.

## Install

Create or download `ReFormatImage.exe`, then run:

```powershell
ReFormatImage.exe --install
```

This installs the context menu entries for the current Windows user under `HKCU`. Administrator access is not required.

To remove the entries:

```powershell
ReFormatImage.exe --uninstall
```

## Context Menu

After installation, common image files show a classic context menu submenu:

```text
ReFormat Image
  Convert to PNG
  Convert to JPG (lossy)
  Convert to WebP
  Convert to BMP
  Convert to TIFF
```

Windows 10 shows these entries in the normal classic context menu. On Windows 11, v1 uses the classic context menu available through **Show more options**.

## CLI Usage

```powershell
ReFormatImage.exe --convert "C:\Images\test.webp" --to png
ReFormatImage.exe --convert "C:\Images\test.png" --to jpg
ReFormatImage.exe --convert "C:\Images\test.png" --to webp --quality 90
ReFormatImage.exe --convert "C:\Images\transparent.png" --to jpg --background "#FFFFFF"
```

Converted files are saved next to the original. Existing files are never overwritten:

```text
image.webp -> image.png
image.webp -> image (1).png
image.webp -> image (2).png
```

## Conversion Notes

- JPG is lossy.
- WebP output may use lossy compression.
- Converting JPG to PNG does not restore the original quality; it stores the already-compressed pixels in a lossless container.
- Converting an image with transparency to JPG flattens the transparent areas onto a background color. The default background is white.
- EXIF orientation is applied where possible.
- ICC profile and EXIF data are preserved where feasible, but some metadata may not survive conversion.
- Animated images are rejected with a clear message.

## Build

Install development dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Build a single executable:

```powershell
.\build.ps1
```

The executable is written to:

```text
dist\ReFormatImage.exe
```

Direct PyInstaller command:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --onefile --name ReFormatImage --clean --paths src src\reformat_image\cli.py
```

## Development

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run from source:

```powershell
.\.venv\Scripts\python.exe -m reformat_image.cli --convert "C:\Images\test.webp" --to png
```

## Limitations and Roadmap

V1 keeps the Windows integration simple and safe by using registry context menu entries. It does not include a COM shell extension, background Explorer processing, overwrite mode, batch conversion, or animated image conversion.

Planned improvements:

- Optional AVIF and HEIC/HEIF support when codec availability is straightforward.
- Batch conversion for multiple selected files.
- Configurable defaults for quality and JPG background color.
- Optional success notifications.
