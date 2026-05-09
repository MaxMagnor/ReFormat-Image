# ReFormat Image

ReFormat Image is a small Windows utility that adds image format conversion to the classic right-click context menu. It is built for quick conversions such as WebP to PNG or JPG without opening a full image editor.

Explorer only launches `ReFormatImage.exe`. Image libraries are not loaded into Explorer.

## Download or Build

The normal installation path is to download `ReFormatImage.exe` from the GitHub Releases page:

<https://github.com/MaxMagnor/ReFormat-Image/releases>

If there is no release yet, build it from source:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The build writes three executables:

```text
dist\ReFormatImage.exe         CLI executable
dist\ReFormatImageContext.exe  hidden context-menu helper
dist\reformat.exe              short CLI alias
```

Direct PyInstaller command:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --onefile --name ReFormatImage --clean --paths src src\reformat_image\cli.py
.\.venv\Scripts\python.exe -m PyInstaller --onefile --noconsole --name ReFormatImageContext --clean --paths src src\reformat_image\cli.py
```

## Install

Run this from the folder containing `ReFormatImage.exe`:

```powershell
ReFormatImage.exe --install
```

This installs the context menu entries for the current Windows user under `HKCU`. Administrator access is not required.

The install command also adds the executable folder to the current user's `PATH`. Open a new terminal after installation, then either command works from anywhere:

```powershell
ReFormatImage --help
reformat --help
```

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
  Convert to GIF
  Convert to ICO
```

Windows 10 shows these entries in the normal classic context menu. On Windows 11, v1.1 uses the classic context menu available through **Show more options**.

The context menu uses `ReFormatImageContext.exe`, which is built without a console window. `ReFormatImage.exe` remains a normal console program so commands like `--help` and `--settings` print correctly.

## Supported Formats

Input and output formats:

- PNG
- JPG / JPEG
- WebP
- BMP
- TIFF / TIF
- GIF, still images only
- ICO

Animated images are not supported yet. AVIF and HEIC/HEIF are not enabled by default because support depends on extra codecs and packaging details.

## CLI Usage

Help:

```powershell
ReFormatImage.exe --help
reformat --help
```

```powershell
ReFormatImage.exe --convert "C:\Images\test.webp" --to png
ReFormatImage.exe --convert "C:\Images\test.png" --to jpg
ReFormatImage.exe --convert "C:\Images\test.png" --to webp --quality 90
ReFormatImage.exe --convert "C:\Images\transparent.png" --to jpg --background "#FFFFFF"
```

Converted files are saved next to the original. By default, existing files are never overwritten:

```text
image.webp -> image.png
image.webp -> image (1).png
image.webp -> image (2).png
```

## Settings

Show the settings file path, current values, descriptions, and examples:

```powershell
ReFormatImage.exe --settings
reformat --settings
```

Change settings:

```powershell
ReFormatImage.exe --set overwrite_existing=true
ReFormatImage.exe --set delete_original_after_conversion=true
ReFormatImage.exe --set show_warnings=true
ReFormatImage.exe --set jpg_quality=85
ReFormatImage.exe --set webp_quality=85
ReFormatImage.exe --set webp_lossless=true
ReFormatImage.exe --set background_color="#FFFFFF"
```

Open the settings file:

```powershell
ReFormatImage.exe --open-settings
```

Reset settings:

```powershell
ReFormatImage.exe --reset-settings
```

Defaults:

- `overwrite_existing`: `false`
- `delete_original_after_conversion`: `false`
- `show_warnings`: `false`
- `jpg_quality`: `90`
- `webp_quality`: `90`
- `webp_lossless`: `false`
- `background_color`: `"#FFFFFF"`
- `preserve_metadata`: `true`

Per-run overrides are also available:

```powershell
ReFormatImage.exe --convert "C:\Images\test.png" --to jpg --overwrite
ReFormatImage.exe --convert "C:\Images\test.png" --to jpg --no-overwrite
ReFormatImage.exe --convert "C:\Images\test.png" --to jpg --delete-original
ReFormatImage.exe --convert "C:\Images\test.png" --to jpg --show-warnings
```

## Conversion Notes

- JPG is lossy.
- WebP may be lossy unless `webp_lossless=true`.
- GIF output may reduce colors because GIF is palette-based.
- Converting JPG to PNG does not restore the original quality; it stores the already-compressed pixels in a lossless container.
- Converting an image with transparency to JPG flattens transparent areas onto the configured background color.
- EXIF orientation is applied where possible.
- ICC profile and EXIF data are preserved where feasible, but some metadata may not survive conversion.
- Warnings are hidden by default to keep context-menu conversions quiet.
- Errors are still shown when the conversion did not complete.

## Update

Check for and install the latest GitHub release:

```powershell
ReFormatImage.exe --update
```

The updater downloads the `ReFormatImage.exe` asset from the latest GitHub release, stages it under `%LOCALAPPDATA%\ReFormat Image\updates`, and replaces the current executable after it exits.
If the release also includes `ReFormatImageContext.exe` and `reformat.exe`, those are updated at the same time.

## Development

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run from source:

```powershell
.\.venv\Scripts\python.exe -m reformat_image.cli --convert "C:\Images\test.webp" --to png
```

## Making a Release

1. Update the version in `pyproject.toml` and `src\reformat_image\__init__.py`.
2. Run tests.
3. Build with `powershell -ExecutionPolicy Bypass -File .\build.ps1 -Clean`.
4. Create a GitHub release tag such as `v1.1.0`.
5. Upload these release assets with exact names:
   - `ReFormatImage.exe`
   - `ReFormatImageContext.exe`
   - `reformat.exe`

The built-in updater depends on those release asset names staying stable.

## Limitations and Roadmap

V1.1 keeps the Windows integration simple and safe by using registry context menu entries. It does not include a COM shell extension, batch conversion, animated image conversion, AVIF, or HEIC/HEIF.

Planned improvements:

- Batch conversion for multiple selected files.
- Optional AVIF and HEIC/HEIF support when codec availability is straightforward.
- Better icon resources and installer packaging.
