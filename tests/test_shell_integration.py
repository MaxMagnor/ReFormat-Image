from __future__ import annotations

from reformat_image.shell_integration import IMAGE_EXTENSIONS, planned_registry_commands


def test_planned_registry_commands_cover_required_menu_items() -> None:
    commands = planned_registry_commands(r"C:\Tools\ReFormatImage.exe")
    targets = {(command.extension, command.target_format) for command in commands}

    for extension in IMAGE_EXTENSIONS:
        assert (extension, "png") in targets
        assert (extension, "jpg") in targets
        assert (extension, "webp") in targets
        assert (extension, "bmp") in targets
        assert (extension, "tiff") in targets
        assert (extension, "gif") in targets
        assert (extension, "ico") in targets


def test_registry_command_uses_expected_executable_arguments() -> None:
    command = planned_registry_commands(r"C:\Tools\ReFormatImageContext.exe")[0]

    assert command.command == r'"C:\Tools\ReFormatImageContext.exe" --convert "%1" --to png'
    assert r"Software\Classes\SystemFileAssociations" in command.menu_path


def test_jpg_menu_label_mentions_lossy() -> None:
    commands = planned_registry_commands(r"C:\Tools\ReFormatImage.exe")
    jpg_command = next(command for command in commands if command.target_format == "jpg")

    assert jpg_command.label == "Convert to JPG (lossy)"
