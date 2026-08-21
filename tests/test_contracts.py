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

    def test_tag_list_contract_validates_normalized_tags_and_baselines(self) -> None:
        contract = PromptContract.from_dict(
            {
                "name": "tag pair",
                "required_sections": ["Positive Prompt", "Negative Prompt"],
                "tag_lists": {
                    "ascii_only": True,
                    "reject_duplicates": True,
                    "reject_cross_section_duplicates": True,
                    "sections": [
                        {
                            "section": "Positive Prompt",
                            "min_tags": 4,
                            "max_tags": 8,
                            "required_tags": ["masterpiece", "highres"],
                        },
                        {
                            "section": "Negative Prompt",
                            "min_tags": 2,
                            "minimum_required_tag_matches": {
                                "tags": ["lowres", "bad hands", "watermark"],
                                "count": 2,
                            },
                        },
                    ],
                },
            }
        )
        valid = validate_output(
            "### Positive Prompt\nmasterpiece, highres, 1woman, rainy night\n\n"
            "### Negative Prompt\nlowres, bad hands, watermark",
            contract,
        )
        self.assertTrue(valid.valid, valid.issues)
        self.assertEqual(
            valid.metadata["tag_section_counts"],
            {"Positive Prompt": 4, "Negative Prompt": 3},
        )

        invalid = validate_output(
            "### Positive Prompt\nmasterpiece, highres, blue eyes, blue_eyes, 蓝眼睛\n\n"
            "### Negative Prompt\nlowres, blue eyes",
            contract,
        )
        codes = {issue.code for issue in invalid.issues}
        self.assertFalse(invalid.valid)
        self.assertTrue(
            {
                "TAG_LIST_NON_ASCII",
                "TAG_LIST_DUPLICATE",
                "TAG_LIST_CROSS_SECTION_DUPLICATE",
                "TAG_LIST_INSUFFICIENT_BASELINE",
            }.issubset(codes)
        )

    def test_tag_list_configuration_is_bounded_and_declared_sections_are_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "also appear in required_sections"):
            PromptContract.from_dict(
                {
                    "name": "invalid tag heading",
                    "required_sections": ["Positive Prompt"],
                    "tag_lists": {"sections": [{"section": "Negative Prompt"}]},
                }
            )
        with self.assertRaisesRegex(ValueError, "greater than or equal"):
            PromptContract.from_dict(
                {
                    "name": "invalid tag bounds",
                    "required_sections": ["Positive Prompt"],
                    "tag_lists": {
                        "sections": [
                            {"section": "Positive Prompt", "min_tags": 4, "max_tags": 3}
                        ]
                    },
                }
            )


if __name__ == "__main__":
    unittest.main()
