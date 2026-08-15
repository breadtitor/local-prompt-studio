from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ContractReport, ValidationIssue

SUPPORTED_FORMAT_VERSION = 1
MAX_FORBIDDEN_SUBSTRINGS = 32
MAX_PATTERN_CHARS = 256
SECTION_PATTERN = re.compile(
    r"(?m)^(?:\s*#{1,6}\s+([A-Za-z][A-Za-z0-9 _-]{0,80}?)\s*#*\s*$|"
    r"\s*([A-Za-z][A-Za-z0-9 _-]{0,80})\s*:\s*)"
)


def _format_version(value: dict[str, Any]) -> int:
    version = value.get("format_version", SUPPORTED_FORMAT_VERSION)
    if isinstance(version, bool) or not isinstance(version, int):
        raise ValueError("format_version must be an integer")
    if version != SUPPORTED_FORMAT_VERSION:
        raise ValueError(
            f"Unsupported contract format_version {version}; "
            f"supported version is {SUPPORTED_FORMAT_VERSION}"
        )
    return version


def _compile_pattern(pattern: str, field: str) -> re.Pattern[str]:
    if len(pattern) > MAX_PATTERN_CHARS:
        raise ValueError(f"{field} must be at most {MAX_PATTERN_CHARS} characters")
    try:
        return re.compile(pattern)
    except re.error as error:
        raise ValueError(f"{field} is not a valid regular expression: {error}") from error


@dataclass(frozen=True)
class PromptContract:
    name: str
    format_version: int = SUPPORTED_FORMAT_VERSION
    required_sections: tuple[str, ...] = ()
    min_output_chars: int = 1
    max_output_chars: int | None = None
    forbidden_substrings: tuple[str, ...] = ()
    reference_pattern: str | None = None
    reference_index_base: int = 0
    require_all_attachments_referenced: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PromptContract:
        format_version = _format_version(value)
        name = str(value.get("name", "Unnamed contract")).strip() or "Unnamed contract"
        sections_value = value.get("required_sections", [])
        if not isinstance(sections_value, list) or not all(
            isinstance(item, str) and item.strip() for item in sections_value
        ):
            raise ValueError("required_sections must be an array of non-empty strings")
        min_chars = int(value.get("min_output_chars", 1))
        if min_chars < 1:
            raise ValueError("min_output_chars must be positive")
        max_chars_value = value.get("max_output_chars")
        max_chars = int(max_chars_value) if max_chars_value is not None else None
        if max_chars is not None and max_chars < min_chars:
            raise ValueError("max_output_chars must be greater than or equal to min_output_chars")
        forbidden_value = value.get("forbidden_substrings", [])
        if not isinstance(forbidden_value, list) or not all(
            isinstance(item, str) and item.strip() for item in forbidden_value
        ):
            raise ValueError("forbidden_substrings must be an array of non-empty strings")
        if len(forbidden_value) > MAX_FORBIDDEN_SUBSTRINGS:
            raise ValueError(
                f"forbidden_substrings must contain at most {MAX_FORBIDDEN_SUBSTRINGS} entries"
            )
        forbidden_substrings = tuple(item.strip() for item in forbidden_value)
        for index, substring in enumerate(forbidden_substrings):
            if len(substring) > MAX_PATTERN_CHARS:
                raise ValueError(
                    f"forbidden_substrings[{index}] must be at most {MAX_PATTERN_CHARS} characters"
                )
        reference_pattern = value.get("reference_pattern")
        if reference_pattern is not None:
            reference_pattern = str(reference_pattern)
            compiled = _compile_pattern(reference_pattern, "reference_pattern")
            if compiled.groups < 1:
                raise ValueError("reference_pattern must contain a capture group for the index")
        index_base = int(value.get("reference_index_base", 0))
        if index_base not in {0, 1}:
            raise ValueError("reference_index_base must be 0 or 1")
        return cls(
            name=name,
            format_version=format_version,
            required_sections=tuple(item.strip() for item in sections_value),
            min_output_chars=min_chars,
            max_output_chars=max_chars,
            forbidden_substrings=forbidden_substrings,
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
    discovered = tuple(
        (match.group(1) or match.group(2)).strip() for match in SECTION_PATTERN.finditer(text)
    )
    discovered_lower = tuple(section.casefold() for section in discovered)

    if len(normalized_text) < contract.min_output_chars:
        issues.append(
            ValidationIssue(
                "OUTPUT_TOO_SHORT",
                f"Output has {len(normalized_text)} characters; contract requires at least "
                f"{contract.min_output_chars}.",
            )
        )

    if contract.max_output_chars is not None and len(normalized_text) > contract.max_output_chars:
        issues.append(
            ValidationIssue(
                "OUTPUT_TOO_LONG",
                f"Output has {len(normalized_text)} characters; contract allows at most "
                f"{contract.max_output_chars}.",
            )
        )

    matched_forbidden_substrings: list[int] = []
    casefolded_text = text.casefold()
    for index, substring in enumerate(contract.forbidden_substrings):
        if substring.casefold() in casefolded_text:
            matched_forbidden_substrings.append(index)
            issues.append(
                ValidationIssue(
                    "FORBIDDEN_SUBSTRING",
                    f"Output contains forbidden_substrings[{index}].",
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
            "matched_forbidden_substrings": matched_forbidden_substrings,
        },
    )
