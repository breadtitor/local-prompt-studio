from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.skill_schema = json.loads(
            (cls.root / "schemas" / "skill.schema.json").read_text(encoding="utf-8")
        )
        cls.contract_schema = json.loads(
            (cls.root / "schemas" / "contract.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(cls.skill_schema)
        Draft202012Validator.check_schema(cls.contract_schema)

    def test_example_manifests_match_v1_schema(self) -> None:
        validator = Draft202012Validator(self.skill_schema)
        for relative_path in (
            "examples/storyboard-skill/skill.json",
            "examples/write-music-caption/skill.json",
            "examples/write-illustration-tags/skill.json",
        ):
            instance = json.loads((self.root / relative_path).read_text(encoding="utf-8"))
            validator.validate(instance)

    def test_example_contracts_match_v1_schema(self) -> None:
        validator = Draft202012Validator(self.contract_schema)
        for relative_path in (
            "examples/storyboard-skill/contract.json",
            "examples/write-music-caption/contract.json",
            "examples/write-illustration-tags/contract.json",
        ):
            instance = json.loads((self.root / relative_path).read_text(encoding="utf-8"))
            validator.validate(instance)

    def test_future_manifest_version_is_rejected_by_schema(self) -> None:
        instance = {
            "format_version": 2,
            "name": "Future Skill",
            "entrypoint": "SKILL.md",
        }
        errors = list(Draft202012Validator(self.skill_schema).iter_errors(instance))
        self.assertTrue(errors)

    def test_invalid_tag_list_schema_is_rejected(self) -> None:
        instance = {
            "format_version": 1,
            "name": "Invalid tag list",
            "required_sections": ["Positive Prompt"],
            "tag_lists": {"sections": [{"section": "Positive Prompt", "min_tags": 0}]},
        }
        errors = list(Draft202012Validator(self.contract_schema).iter_errors(instance))
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
