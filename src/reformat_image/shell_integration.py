from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .formats import REQUIRED_CONTEXT_MENU_TARGETS, REQUIRED_FORMATS


MENU_KEY_NAME = "ReFormatImage"
MENU_TITLE = "ReFormat Image"
REGISTRY_ROOT = r"Software\Classes\SystemFileAssociations"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".ico")


class ShellIntegrationError(RuntimeError):
    """Raised when context menu integration cannot be installed."""


@dataclass(frozen=True)
class RegistryCommand:
    extension: str
    target_format: str
    menu_path: str
    command: str
    label: str


def install_context_menu(executable_path: str | Path | None = None) -> None:
    if os.name != "nt":
        raise ShellIntegrationError("Context menu integration is only available on Windows.")

    import winreg

    exe = Path(executable_path) if executable_path else resolve_executable_path()
    for extension in IMAGE_EXTENSIONS:
        parent_path = _menu_key_path(extension)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, parent_path) as parent:
            winreg.SetValueEx(parent, "MUIVerb", 0, winreg.REG_SZ, MENU_TITLE)
            winreg.SetValueEx(parent, "SubCommands", 0, winreg.REG_SZ, "")

        shell_path = parent_path + r"\shell"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, shell_path):
            pass

        for target in REQUIRED_CONTEXT_MENU_TARGETS:
            image_format = REQUIRED_FORMATS[target]
            item_path = shell_path + "\\" + target
            command_path = item_path + r"\command"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, item_path) as item:
                winreg.SetValueEx(item, "MUIVerb", 0, winreg.REG_SZ, _menu_label(target))
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_path) as command_key:
                winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, build_command(exe, image_format.key))


def uninstall_context_menu() -> None:
    if os.name != "nt":
        raise ShellIntegrationError("Context menu integration is only available on Windows.")

    import winreg

    for extension in IMAGE_EXTENSIONS:
        key_path = _menu_key_path(extension)
        try:
            _delete_tree(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            continue


def planned_registry_commands(executable_path: str | Path) -> list[RegistryCommand]:
    exe = Path(executable_path)
    commands: list[RegistryCommand] = []
    for extension in IMAGE_EXTENSIONS:
        for target in REQUIRED_CONTEXT_MENU_TARGETS:
            commands.append(
                RegistryCommand(
                    extension=extension,
                    target_format=target,
                    menu_path=_menu_key_path(extension) + rf"\shell\{target}\command",
                    command=build_command(exe, target),
                    label=_menu_label(target),
                )
            )
    return commands


def resolve_executable_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()

    # Development mode: use the running Python interpreter and module entrypoint.
    return Path(sys.executable).resolve()


def build_command(executable_path: str | Path, target_format: str) -> str:
    exe = Path(executable_path)
    if exe.name.lower().startswith("python"):
        return f'"{exe}" -m reformat_image.cli --convert "%1" --to {target_format}'
    exe_literal = _powershell_single_quoted(str(exe))
    command = f"& {exe_literal} --convert $args[0] --to {target_format}"
    return f'powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "{command}" "%1"'


def _powershell_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _menu_key_path(extension: str) -> str:
    return rf"{REGISTRY_ROOT}\{extension}\shell\{MENU_KEY_NAME}"


def _menu_label(target_format: str) -> str:
    image_format = REQUIRED_FORMATS[target_format]
    suffix = " (lossy)" if target_format == "jpg" else ""
    return f"Convert to {image_format.label}{suffix}"


def _delete_tree(root, subkey: str) -> None:
    import winreg

    with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        while True:
            try:
                child = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_tree(key, child)
    winreg.DeleteKey(root, subkey)
