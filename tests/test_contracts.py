from __future__ import annotations

import unittest

from local_prompt_studio.contracts import PromptContract, validate_output


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = PromptContract.from_dict(
            {
                "name": "test contract",
                "required_sections": ["summary", "details", "constraints"],
                "min_output_chars": 30,
                "reference_pattern": r"@image_(\d+)",
                "reference_index_base": 0,
                "require_all_attachments_referenced": True,
            }
        )

    def test_valid_output_passes(self) -> None:
        report = validate_output(
            "summary: calm scene\ndetails: apply @image_0 carefully\nconstraints: no text",
            self.contract,
            attachment_count=1,
        )
        self.assertTrue(report.valid)
        self.assertEqual(report.issues, ())
        self.assertEqual(report.metadata["referenced_indices"], [0])

    def test_missing_reordered_and_unknown_references_fail(self) -> None:
        report = validate_output(
            "details: use @image_2\nsummary: short",
            self.contract,
            attachment_count=1,
        )
        codes = [issue.code for issue in report.issues]
        self.assertFalse(report.valid)
        self.assertIn("MISSING_SECTION", codes)
        self.assertIn("SECTION_ORDER", codes)
        self.assertIn("UNKNOWN_ATTACHMENT_REFERENCE", codes)
        self.assertIn("UNUSED_ATTACHMENT", codes)

    def test_short_output_fails_minimum_length(self) -> None:
        contract = PromptContract.from_dict(
            {
                "name": "minimum length",
                "min_output_chars": 100,
            }
        )
        report = validate_output("too short", contract)
        self.assertFalse(report.valid)
        self.assertIn("OUTPUT_TOO_SHORT", [issue.code for issue in report.issues])

    def test_markdown_headings_and_forbidden_substrings(self) -> None:
        contract = PromptContract.from_dict(
            {
                "format_version": 1,
                "name": "music caption",
                "required_sections": ["Global Metadata", "Vocal Details", "Arrangement"],
                "min_output_chars": 80,
                "max_output_chars": 500,
                "forbidden_substrings": ["template_id", "```"],
            }
        )
        text = "\n".join(
            [
                "### Global Metadata",
                "Instrumental electronic score with a restrained slow build.",
                "### Vocal Details",
                "Instrumental; the lead melody stays with a glassy synthesizer.",
                "### Arrangement",
                "Sparse intro, layered development, focused climax, and a clean outro.",
            ]
        )
        report = validate_output(text, contract)
        self.assertTrue(report.valid)
        self.assertEqual(
            report.discovered_sections,
            ("Global Metadata", "Vocal Details", "Arrangement"),
        )

        forbidden = validate_output(f"{text}\ntemplate_id: copied", contract)
        self.assertFalse(forbidden.valid)
        self.assertIn("FORBIDDEN_SUBSTRING", [issue.code for issue in forbidden.issues])

    def test_maximum_length_and_invalid_guard_configuration(self) -> None:
        contract = PromptContract.from_dict(
            {"name": "bounded", "min_output_chars": 2, "max_output_chars": 4}
        )
        report = validate_output("12345", contract)
        self.assertFalse(report.valid)
        self.assertIn("OUTPUT_TOO_LONG", [issue.code for issue in report.issues])

        with self.assertRaisesRegex(ValueError, "greater than or equal"):
            PromptContract.from_dict(
                {"name": "invalid", "min_output_chars": 10, "max_output_chars": 5}
            )
        with self.assertRaisesRegex(ValueError, "at most"):
            PromptContract.from_dict({"name": "invalid", "forbidden_substrings": ["x" * 257]})


if __name__ == "__main__":
    unittest.main()
