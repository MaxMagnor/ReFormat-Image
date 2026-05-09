from __future__ import annotations

import os
from pathlib import Path


class PathIntegrationError(RuntimeError):
    """Raised when the user PATH cannot be updated."""


def add_directory_to_user_path(directory: str | Path) -> bool:
    if os.name != "nt":
        raise PathIntegrationError("PATH integration is only available on Windows.")

    import winreg

    path_dir = str(Path(directory).resolve())
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        current = _read_path_value(key, winreg)
        parts = _split_path(current)
        if any(_same_path(part, path_dir) for part in parts):
            return False
        parts.append(path_dir)
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, os.pathsep.join(parts))

    _broadcast_environment_change()
    return True


def remove_directory_from_user_path(directory: str | Path) -> bool:
    if os.name != "nt":
        raise PathIntegrationError("PATH integration is only available on Windows.")

    import winreg

    path_dir = str(Path(directory).resolve())
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        current = _read_path_value(key, winreg)
        parts = [part for part in _split_path(current) if not _same_path(part, path_dir)]
        if os.pathsep.join(parts) == current:
            return False
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, os.pathsep.join(parts))

    _broadcast_environment_change()
    return True


def _read_path_value(key, winreg_module) -> str:
    try:
        value, _value_type = winreg_module.QueryValueEx(key, "Path")
    except FileNotFoundError:
        return ""
    return str(value)


def _split_path(value: str) -> list[str]:
    return [part for part in value.split(os.pathsep) if part]


def _same_path(left: str, right: str) -> bool:
    return str(Path(left)).casefold() == str(Path(right)).casefold()


def _broadcast_environment_change() -> None:
    try:
        import ctypes

        hwnd_broadcast = 0xFFFF
        wm_settingchange = 0x001A
        smto_abortifhung = 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            hwnd_broadcast,
            wm_settingchange,
            0,
            "Environment",
            smto_abortifhung,
            5000,
            None,
        )
    except OSError:
        return
