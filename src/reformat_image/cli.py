from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from reformat_image.console import attach_parent_console
from reformat_image.converter import ConversionError, convert_image
from reformat_image.notifications import show_error, show_info, show_warning
from reformat_image.path_integration import PathIntegrationError, add_directory_to_user_path, remove_directory_from_user_path
from reformat_image.settings import (
    SettingsError,
    load_settings,
    reset_settings,
    save_settings,
    settings_help,
    update_setting,
)
from reformat_image.shell_integration import ShellIntegrationError, install_context_menu, uninstall_context_menu
from reformat_image.updater import UpdateError, update_application


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ReFormatImage", description="Convert image files from the command line or Windows context menu.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--install", action="store_true", help="Install Windows context menu entries for the current user.")
    action.add_argument("--uninstall", action="store_true", help="Remove Windows context menu entries for the current user.")
    action.add_argument("--convert", metavar="PATH", help="Image file to convert.")
    action.add_argument("--settings", action="store_true", help="Show available settings, current values, and examples.")
    action.add_argument("--reset-settings", action="store_true", help="Reset settings to defaults.")
    action.add_argument("--open-settings", action="store_true", help="Open the settings file in the default editor.")
    action.add_argument("--update", action="store_true", help="Download and install the latest GitHub release.")
    action.add_argument("--set", dest="settings_updates", action="append", metavar="KEY=VALUE", help="Update one setting. Can be used multiple times.")
    parser.add_argument("--to", dest="to_format", help="Target format: png, jpg, webp, bmp, tiff, gif, or ico.")
    parser.add_argument("--quality", type=int, help="Quality for lossy output formats, from 1 to 100.")
    parser.add_argument("--background", help="Background color for flattening transparency to JPG. Default comes from settings.")
    parser.add_argument("--overwrite", dest="overwrite_existing", action="store_true", default=None, help="Overwrite the target output file for this conversion.")
    parser.add_argument("--no-overwrite", dest="overwrite_existing", action="store_false", help="Use safe numbered output names for this conversion.")
    parser.add_argument("--delete-original", action="store_true", help="Delete the original after a successful conversion.")
    parser.add_argument("--show-warnings", action="store_true", help="Show conversion warnings for this run.")
    parser.add_argument("--quiet", action="store_true", help="Suppress Windows dialogs and print messages to the console.")
    return parser


def main(argv: list[str] | None = None) -> int:
    if getattr(sys, "frozen", False):
        attach_parent_console()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = load_settings()
        if args.settings_updates:
            for assignment in args.settings_updates:
                settings = update_setting(settings, assignment)
            save_settings(settings)
            print(settings_help(settings))
            return 0

        if args.settings:
            print(settings_help(settings))
            return 0

        if args.reset_settings:
            reset_settings()
            show_info("Settings reset to defaults.", quiet=args.quiet)
            return 0

        if args.open_settings:
            path = save_settings(settings)
            _open_path(path)
            return 0

        if args.update:
            result = update_application()
            if result.update_available:
                show_info(result.message, quiet=args.quiet)
            else:
                print(result.message)
            return 0

        if args.install:
            install_context_menu()
            path_added = add_directory_to_user_path(Path(sys.executable).resolve().parent)
            message = "Context menu entries installed for the current user."
            if path_added:
                message += " The install folder was added to your user PATH. Open a new terminal to use ReFormatImage or reformat from anywhere."
            show_info(message, quiet=args.quiet)
            return 0

        if args.uninstall:
            uninstall_context_menu()
            remove_directory_from_user_path(Path(sys.executable).resolve().parent)
            show_info("Context menu entries removed for the current user.", quiet=args.quiet)
            return 0

        if args.convert:
            if not args.to_format:
                parser.error("--to is required when using --convert")
            result = convert_image(
                args.convert,
                args.to_format,
                quality=args.quality,
                jpg_quality=settings.jpg_quality,
                webp_quality=settings.webp_quality,
                webp_lossless=settings.webp_lossless,
                background=args.background or settings.background_color,
                overwrite_existing=settings.overwrite_existing if args.overwrite_existing is None else args.overwrite_existing,
                delete_original_after_conversion=settings.delete_original_after_conversion or args.delete_original,
                preserve_metadata=settings.preserve_metadata,
            )
            if result.warnings and (settings.show_warnings or args.show_warnings):
                show_warning("\n".join(result.warnings), quiet=args.quiet)
            else:
                print(f"Saved: {result.output_path}")
            return 0

    except (ConversionError, PathIntegrationError, SettingsError, ShellIntegrationError, UpdateError) as exc:
        show_error(str(exc), quiet=getattr(args, "quiet", False))
        return 1

    return 0


def _open_path(path) -> None:
    if os.name != "nt":
        print(path)
        return
    os.startfile(path)  # type: ignore[attr-defined]


if __name__ == "__main__":
    sys.exit(main())
