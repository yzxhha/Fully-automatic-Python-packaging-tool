import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import packager


class DiscoverEntryTests(unittest.TestCase):
    def test_prefers_main_py(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("", encoding="utf-8")
            (root / "app.py").write_text("", encoding="utf-8")
            self.assertEqual(packager.discover_entry(root), root / "main.py")

    def test_uses_only_root_python_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tool.py").write_text("", encoding="utf-8")
            self.assertEqual(packager.discover_entry(root), root / "tool.py")

    def test_raises_for_ambiguous_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "alpha.py").write_text("", encoding="utf-8")
            (root / "beta.py").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "多个入口"):
                packager.discover_entry(root)


class CommandTests(unittest.TestCase):
    def test_command_includes_mode_and_options_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "main.py"
            entry.touch()
            icon = root / "app.ico"
            icon.touch()
            data = root / "assets"
            data.mkdir()
            command = packager.build_command(
                entry=entry,
                project=root,
                name="Sample",
                mode="onedir",
                output=root / "dist",
                work=root / "build",
                spec=root / "spec",
                windowed=True,
                icon=icon,
                add_data=[(data, "assets")],
                hidden_imports=["sample.plugin"],
                clean=True,
            )
            self.assertIn("--onedir", command)
            self.assertIn("--windowed", command)
            self.assertIn("--clean", command)
            self.assertIn("--hidden-import", command)
            self.assertEqual(command[-1], str(entry))

    def test_data_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "assets"
            source.mkdir()
            parsed_source, destination = packager.parse_data_mapping(f"{source}=data")
            self.assertEqual(parsed_source, source.resolve())
            self.assertEqual(destination, "data")

    def test_parser_defaults(self):
        args = packager.make_parser().parse_args([])
        self.assertEqual(args.mode, "onefile")
        self.assertEqual(args.project, ".")


if __name__ == "__main__":
    unittest.main()
