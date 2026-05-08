from __future__ import annotations

import ctypes
import sys
from os import name as os_name


APP_TITLE = "ReFormat Image"


def show_error(message: str, *, quiet: bool = False) -> None:
    _show(message, flags=0x10, quiet=quiet, stream=sys.stderr)


def show_warning(message: str, *, quiet: bool = False) -> None:
    _show(message, flags=0x30, quiet=quiet, stream=sys.stderr)


def show_info(message: str, *, quiet: bool = False) -> None:
    _show(message, flags=0x40, quiet=quiet, stream=sys.stdout)


def _show(message: str, *, flags: int, quiet: bool, stream) -> None:
    if quiet:
        print(message, file=stream)
        return

    if os_name == "nt":
        ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, flags)
        return

    print(message, file=stream)
