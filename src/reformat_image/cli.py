from __future__ import annotations

import argparse
import sys

from reformat_image.converter import ConversionError, convert_image
from reformat_image.notifications import show_error, show_info, show_warning
from reformat_image.shell_integration import ShellIntegrationError, install_context_menu, uninstall_context_menu


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ReFormatImage", description="Convert image files from the command line or Windows context menu.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--install", action="store_true", help="Install Windows context menu entries for the current user.")
    action.add_argument("--uninstall", action="store_true", help="Remove Windows context menu entries for the current user.")
    action.add_argument("--convert", metavar="PATH", help="Image file to convert.")
    parser.add_argument("--to", dest="to_format", help="Target format: png, jpg, webp, bmp, or tiff.")
    parser.add_argument("--quality", type=int, default=90, help="Quality for lossy output formats, from 1 to 100. Default: 90.")
    parser.add_argument("--background", default="#FFFFFF", help="Background color for flattening transparency to JPG. Default: #FFFFFF.")
    parser.add_argument("--quiet", action="store_true", help="Suppress Windows dialogs and print messages to the console.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.install:
            install_context_menu()
            show_info("Context menu entries installed for the current user.", quiet=args.quiet)
            return 0

        if args.uninstall:
            uninstall_context_menu()
            show_info("Context menu entries removed for the current user.", quiet=args.quiet)
            return 0

        if args.convert:
            if not args.to_format:
                parser.error("--to is required when using --convert")
            result = convert_image(
                args.convert,
                args.to_format,
                quality=args.quality,
                background=args.background,
            )
            if result.warnings:
                show_warning("\n".join(result.warnings), quiet=args.quiet)
            else:
                print(f"Saved: {result.output_path}")
            return 0

    except (ConversionError, ShellIntegrationError) as exc:
        show_error(str(exc), quiet=args.quiet)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
