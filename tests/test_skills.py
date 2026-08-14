from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from local_prompt_studio.skills import load_skill_package


class SkillPackageTests(unittest.TestCase):
    def _skill_directory(self, root: Path) -> Path:
        skill = root / "skill"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: test-skill\n---\n\nFollow the reference.", encoding="utf-8"
        )
        (skill / "references" / "format.md").write_text("summary: then details:", encoding="utf-8")
        (skill / "ignored.py").write_text("raise RuntimeError('must not run')", encoding="utf-8")
        (skill / "contract.json").write_text(
            json.dumps({"name": "contract", "required_sections": ["summary"]}),
            encoding="utf-8",
        )
        return skill

    def test_directory_without_manifest_loads_text_references_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = load_skill_package(self._skill_directory(Path(directory)))
            self.assertEqual(package.name, "test-skill")
            self.assertEqual(package.included_files, ("SKILL.md", "references/format.md"))
            self.assertNotIn("must not run", package.prompt_text)
            self.assertEqual(package.contract.name, "contract")  # type: ignore[union-attr]
            self.assertTrue(package.warnings)

    def test_zip_package_loads_without_extracting_or_executing_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = self._skill_directory(root)
            archive_path = root / "skill.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for path in skill.rglob("*"):
                    if path.is_file():
                        archive.write(path, f"package/{path.relative_to(skill).as_posix()}")
            package = load_skill_package(archive_path)
            self.assertEqual(package.name, "test-skill")
            self.assertIn("summary: then details:", package.prompt_text)

    def test_zip_traversal_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../SKILL.md", "unsafe")
            with self.assertRaisesRegex(ValueError, "safely relative"):
                load_skill_package(archive_path)


if __name__ == "__main__":
    unittest.main()
