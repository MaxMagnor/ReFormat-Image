from __future__ import annotations

import ctypes
import os
import sys


ATTACH_PARENT_PROCESS = -1


def attach_parent_console() -> None:
    if os.name != "nt":
        return
    if sys.stdout and sys.stdout.isatty():
        return

    try:
        if not ctypes.windll.kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
            return
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        sys.stdin = open("CONIN$", "r", encoding="utf-8")
    except OSError:
        return
