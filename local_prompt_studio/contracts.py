from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ContractReport, ValidationIssue

SECTION_PATTERN = re.compile(r"(?m)^\s*([A-Za-z][A-Za-z0-9 _-]{0,80})\s*:\s*")


@dataclass(frozen=True)
class PromptContract:
    name: str
    required_sections: tuple[str, ...] = ()
    min_output_chars: int = 1
    reference_pattern: str | None = None
    reference_index_base: int = 0
    require_all_attachments_referenced: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PromptContract:
        name = str(value.get("name", "Unnamed contract")).strip() or "Unnamed contract"
        sections_value = value.get("required_sections", [])
        if not isinstance(sections_value, list) or not all(
            isinstance(item, str) and item.strip() for item in sections_value
        ):
            raise ValueError("required_sections must be an array of non-empty strings")
        min_chars = int(value.get("min_output_chars", 1))
        if min_chars < 1:
            raise ValueError("min_output_chars must be positive")
        reference_pattern = value.get("reference_pattern")
        if reference_pattern is not None:
            reference_pattern = str(reference_pattern)
            compiled = re.compile(reference_pattern)
            if compiled.groups < 1:
                raise ValueError("reference_pattern must contain a capture group for the index")
        index_base = int(value.get("reference_index_base", 0))
        if index_base not in {0, 1}:
            raise ValueError("reference_index_base must be 0 or 1")
        return cls(
            name=name,
            required_sections=tuple(item.strip() for item in sections_value),
            min_output_chars=min_chars,
            reference_pattern=reference_pattern,
            reference_index_base=index_base,
            require_all_attachments_referenced=bool(
                value.get("require_all_attachments_referenced", False)
            ),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> PromptContract:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("contract JSON must contain an object")
        return cls.from_dict(raw)


def validate_output(
    text: str,
    contract: PromptContract,
    attachment_count: int = 0,
) -> ContractReport:
    issues: list[ValidationIssue] = []
    normalized_text = text.strip()
    discovered = tuple(match.group(1).strip() for match in SECTION_PATTERN.finditer(text))
    discovered_lower = tuple(section.casefold() for section in discovered)

    if len(normalized_text) < contract.min_output_chars:
        issues.append(
            ValidationIssue(
                "OUTPUT_TOO_SHORT",
                f"Output has {len(normalized_text)} characters; contract requires at least "
                f"{contract.min_output_chars}.",
            )
        )

    positions: list[int] = []
    for required in contract.required_sections:
        key = required.casefold()
        count = discovered_lower.count(key)
        if count == 0:
            issues.append(
                ValidationIssue("MISSING_SECTION", f"Required section is missing: {required}")
            )
            continue
        if count > 1:
            issues.append(
                ValidationIssue("DUPLICATE_SECTION", f"Section appears more than once: {required}")
            )
        positions.append(discovered_lower.index(key))
    if positions != sorted(positions):
        issues.append(
            ValidationIssue("SECTION_ORDER", "Required sections are not in the configured order.")
        )

    referenced_indices: set[int] = set()
    if contract.reference_pattern:
        for match in re.finditer(contract.reference_pattern, text):
            index = int(match.group(1))
            referenced_indices.add(index)
            minimum = contract.reference_index_base
            maximum = contract.reference_index_base + attachment_count - 1
            if attachment_count == 0 or index < minimum or index > maximum:
                issues.append(
                    ValidationIssue(
                        "UNKNOWN_ATTACHMENT_REFERENCE",
                        f"Reference index {index} does not map to one of the {attachment_count} "
                        "attached files.",
                    )
                )
        if contract.require_all_attachments_referenced and attachment_count > 0:
            expected = set(
                range(
                    contract.reference_index_base,
                    contract.reference_index_base + attachment_count,
                )
            )
            missing = sorted(expected - referenced_indices)
            if missing:
                issues.append(
                    ValidationIssue(
                        "UNUSED_ATTACHMENT",
                        f"Attached file indices are not referenced: {', '.join(map(str, missing))}",
                        "warning",
                    )
                )

    return ContractReport(
        valid=not any(issue.severity == "error" for issue in issues),
        contract_name=contract.name,
        discovered_sections=discovered,
        issues=tuple(issues),
        metadata={
            "characters": len(normalized_text),
            "attachment_count": attachment_count,
            "referenced_indices": sorted(referenced_indices),
        },
    )
