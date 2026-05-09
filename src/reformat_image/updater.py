from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import __version__


LATEST_RELEASE_URL = "https://api.github.com/repos/MaxMagnor/ReFormat-Image/releases/latest"
ASSET_NAME = "ReFormatImage.exe"
OPTIONAL_ASSET_NAMES = ("ReFormatImageContext.exe", "reformat.exe")
APP_DIR_NAME = "ReFormat Image"


class UpdateError(RuntimeError):
    """Raised when the updater cannot complete."""


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    assets: tuple[ReleaseAsset, ...]


@dataclass(frozen=True)
class UpdateResult:
    message: str
    update_available: bool
    staged_path: Path | None = None
    staged_paths: tuple[Path, ...] = ()


def update_application(
    *,
    current_exe: Path | None = None,
    release_url: str = LATEST_RELEASE_URL,
    launch_helper: bool = True,
) -> UpdateResult:
    exe_path = current_exe or _packaged_executable_path()
    if exe_path is None:
        raise UpdateError("Updater is only available from the packaged ReFormatImage.exe.")

    release = fetch_latest_release(release_url)
    if _version_tuple(release.tag) <= _version_tuple(__version__):
        return UpdateResult(f"ReFormat Image is already up to date ({__version__}).", False)

    staged_paths = _download_release_assets(release, release.tag)
    helper_path = create_replacement_helper(exe_path, staged_paths)
    if launch_helper:
        subprocess.Popen(["cmd.exe", "/c", str(helper_path)], creationflags=_creation_flags())
    return UpdateResult(
        f"Update {release.tag} downloaded. ReFormat Image will replace itself after exit.",
        True,
        staged_paths[0],
        staged_paths,
    )


def fetch_latest_release(release_url: str = LATEST_RELEASE_URL) -> ReleaseInfo:
    request = urllib.request.Request(release_url, headers={"Accept": "application/vnd.github+json", "User-Agent": "ReFormatImage"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except OSError as exc:
        raise UpdateError(f"Could not check for updates: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise UpdateError("GitHub returned an invalid update response.") from exc

    assets = tuple(
        ReleaseAsset(name=str(asset.get("name", "")), download_url=str(asset.get("browser_download_url", "")))
        for asset in payload.get("assets", [])
        if isinstance(asset, dict)
    )
    return ReleaseInfo(tag=str(payload.get("tag_name", "")), assets=assets)


def download_asset(url: str, release_tag: str, asset_name: str = ASSET_NAME) -> Path:
    if not url:
        raise UpdateError("Release asset is missing a download URL.")

    destination = update_dir() / release_tag / asset_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="ReFormatImage-", suffix=".exe", dir=destination.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, temp_path.open("wb") as output:
            shutil.copyfileobj(response, output)
        temp_path.replace(destination)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        raise UpdateError(f"Could not download update: {exc}") from exc
    return destination


def update_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if root:
        return Path(root) / APP_DIR_NAME / "updates"
    return Path.home() / "AppData" / "Local" / APP_DIR_NAME / "updates"


def create_replacement_helper(current_exe: Path, staged_exes: Path | tuple[Path, ...]) -> Path:
    staged_paths = (staged_exes,) if isinstance(staged_exes, Path) else staged_exes
    helper_path = staged_paths[0].with_suffix(".cmd")
    install_dir = current_exe.parent
    move_lines = []
    for staged_path in staged_paths:
        target = install_dir / staged_path.name
        move_lines.append(f'move /y "{staged_path}" "{target}" >nul')
        move_lines.append("if errorlevel 1 goto wait")
    script = f"""@echo off
setlocal
set "TARGET={current_exe}"
:wait
timeout /t 1 /nobreak >nul
{os.linesep.join(move_lines)}
start "" "%TARGET%"
endlocal
"""
    helper_path.write_text(script, encoding="utf-8")
    return helper_path


def _packaged_executable_path() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable).resolve()


def _find_asset(release: ReleaseInfo, name: str) -> ReleaseAsset:
    for asset in release.assets:
        if asset.name == name:
            return asset
    raise UpdateError(f"Latest release does not include {name}.")


def _download_release_assets(release: ReleaseInfo, release_tag: str) -> tuple[Path, ...]:
    required = _find_asset(release, ASSET_NAME)
    assets_by_name = {asset.name: asset for asset in release.assets}
    staged = [download_asset(required.download_url, release_tag, required.name)]
    for name in OPTIONAL_ASSET_NAMES:
        asset = assets_by_name.get(name)
        if asset is not None:
            staged.append(download_asset(asset.download_url, release_tag, asset.name))
    return tuple(staged)


def _version_tuple(value: str) -> tuple[int, ...]:
    normalized = value.strip().lower().lstrip("v")
    parts: list[int] = []
    for part in normalized.split("."):
        number = ""
        for char in part:
            if not char.isdigit():
                break
            number += char
        parts.append(int(number or "0"))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts or [0, 0, 0])


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
