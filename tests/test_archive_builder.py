import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import archive_builder
from archive_builder import ARCHIVE_FORMATS, create_archive


class ArchiveBuilderTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        project = root / "sample"
        project.mkdir()
        (project / "main.py").write_text("print('hello')", encoding="utf-8")
        (project / "settings.json").write_text("{}", encoding="utf-8")
        (project / "images").mkdir()
        (project / "images" / "logo.png").write_bytes(b"png-data")
        (project / ".venv").mkdir()
        (project / ".venv" / "secret.txt").write_text("ignored", encoding="utf-8")
        (project / "__pycache__").mkdir()
        (project / "__pycache__" / "main.pyc").write_bytes(b"bytecode")
        (project / "build").mkdir()
        (project / "build" / "old.bin").write_bytes(b"old")
        return project

    def test_zip_contains_common_file_types_and_excludes_build_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = self.make_project(root)
            output = root / "sample.zip"
            create_archive(project, output, "ZIP (.zip)")
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
            self.assertIn("sample/main.py", names)
            self.assertIn("sample/settings.json", names)
            self.assertIn("sample/images/logo.png", names)
            self.assertFalse(any(".venv" in name or "__pycache__" in name or "/build/" in name for name in names))

    def test_archive_formats_are_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = self.make_project(root)
            for label, (extension, _kind) in ARCHIVE_FORMATS.items():
                output = root / ("bundle" + extension)
                create_archive(project, output, label)
                self.assertTrue(output.is_file(), label)
                self.assertGreater(output.stat().st_size, 0)

    def test_output_inside_project_is_not_archived_into_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.make_project(Path(directory))
            output = project / "dist" / "sample.zip"
            create_archive(project, output, "ZIP (.zip)")
            with zipfile.ZipFile(output) as archive:
                self.assertNotIn("sample/dist/sample.zip", archive.namelist())

    def test_rejects_wrong_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.make_project(Path(directory))
            with self.assertRaisesRegex(ValueError, "扩展名"):
                create_archive(project, Path(directory) / "sample.tar", "ZIP (.zip)")

    def test_failed_write_preserves_existing_archive_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = self.make_project(root)
            output = root / "sample.zip"
            output.write_bytes(b"previous archive")
            with patch.object(archive_builder.zipfile, "ZipFile", side_effect=OSError("disk error")):
                with self.assertRaisesRegex(OSError, "disk error"):
                    create_archive(project, output, "ZIP (.zip)")
            self.assertEqual(output.read_bytes(), b"previous archive")
            self.assertEqual(list(root.glob(".sample.zip.*.tmp")), [])

    def test_case_insensitive_bytecode_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.make_project(Path(directory))
            (project / "module.PYC").write_bytes(b"bytecode")
            paths = list(archive_builder.iter_project_files(project))
            self.assertFalse(any(path.name.lower().endswith(".pyc") for path in paths))


if __name__ == "__main__":
    unittest.main()
