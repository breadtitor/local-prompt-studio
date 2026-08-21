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
MAX_TAG_LIST_SECTIONS = 8
MAX_TAGS_PER_SECTION = 200
MAX_TAGS_IN_RULE = 32
MAX_TAG_CHARS = 80
SECTION_PATTERN = re.compile(
    r"(?m)^(?:\s*#{1,6}\s+([A-Za-z][A-Za-z0-9 _-]{0,80}?)\s*#*\s*$|"
    r"\s*([A-Za-z][A-Za-z0-9 _-]{0,80})\s*:\s*)"
)


def _normalize_tag(tag: str) -> str:
    """Normalize harmless spelling variants without interpreting model syntax."""
    normalized = tag.strip().casefold().replace("_", " ")
    normalized = re.sub(r"^\(+|\)+$", "", normalized)
    normalized = re.sub(r":\s*-?\d+(?:\.\d+)?$", "", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


@dataclass(frozen=True)
class MinimumRequiredTagMatches:
    tags: tuple[str, ...]
    count: int


@dataclass(frozen=True)
class TagListSection:
    section: str
    min_tags: int = 1
    max_tags: int | None = None
    required_tags: tuple[str, ...] = ()
    minimum_required_tag_matches: MinimumRequiredTagMatches | None = None


@dataclass(frozen=True)
class TagListRules:
    sections: tuple[TagListSection, ...]
    ascii_only: bool = False
    reject_duplicates: bool = False
    reject_cross_section_duplicates: bool = False


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


def _positive_int(value: object, field: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < 1 or value > maximum:
        raise ValueError(f"{field} must be between 1 and {maximum}")
    return value


def _tag_values(value: object, field: str, minimum_items: int = 0) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) < minimum_items or len(value) > MAX_TAGS_IN_RULE:
        raise ValueError(
            f"{field} must be an array with {minimum_items} to {MAX_TAGS_IN_RULE} entries"
        )
    if not all(
        isinstance(item, str) and item.strip() and len(item.strip()) <= MAX_TAG_CHARS
        for item in value
    ):
        raise ValueError(f"{field} must contain non-empty strings up to {MAX_TAG_CHARS} characters")
    normalized = tuple(_normalize_tag(item) for item in value)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field} must not contain duplicate normalized tags")
    return normalized


def _tag_list_rules(value: object, required_sections: tuple[str, ...]) -> TagListRules | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("tag_lists must be an object")
    allowed = {
        "ascii_only",
        "reject_duplicates",
        "reject_cross_section_duplicates",
        "sections",
    }
    extra = sorted(set(value).difference(allowed))
    if extra:
        raise ValueError(f"tag_lists contains unsupported properties: {', '.join(extra)}")
    sections_value = value.get("sections")
    if (
        not isinstance(sections_value, list)
        or not 1 <= len(sections_value) <= MAX_TAG_LIST_SECTIONS
    ):
        raise ValueError(
            f"tag_lists.sections must contain 1 to {MAX_TAG_LIST_SECTIONS} section definitions"
        )
    section_rules: list[TagListSection] = []
    normalized_sections: set[str] = set()
    required_section_names = {section.casefold() for section in required_sections}
    for index, item in enumerate(sections_value):
        field = f"tag_lists.sections[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{field} must be an object")
        allowed_section = {
            "section",
            "min_tags",
            "max_tags",
            "required_tags",
            "minimum_required_tag_matches",
        }
        extra = sorted(set(item).difference(allowed_section))
        if extra:
            raise ValueError(f"{field} contains unsupported properties: {', '.join(extra)}")
        section_name = item.get("section")
        if (
            not isinstance(section_name, str)
            or not section_name.strip()
            or len(section_name.strip()) > 81
        ):
            raise ValueError(f"{field}.section must be a non-empty string up to 81 characters")
        section_name = section_name.strip()
        normalized_section = section_name.casefold()
        if normalized_section in normalized_sections:
            raise ValueError("tag_lists.sections must not repeat section names")
        if normalized_section not in required_section_names:
            raise ValueError(
                f"{field}.section must also appear in required_sections: {section_name}"
            )
        normalized_sections.add(normalized_section)
        min_tags = _positive_int(item.get("min_tags", 1), f"{field}.min_tags", MAX_TAGS_PER_SECTION)
        max_value = item.get("max_tags")
        max_tags = (
            _positive_int(max_value, f"{field}.max_tags", MAX_TAGS_PER_SECTION)
            if max_value is not None
            else None
        )
        if max_tags is not None and max_tags < min_tags:
            raise ValueError(f"{field}.max_tags must be greater than or equal to min_tags")
        required_tags = _tag_values(item.get("required_tags", []), f"{field}.required_tags")
        match_value = item.get("minimum_required_tag_matches")
        minimum_matches = None
        if match_value is not None:
            if not isinstance(match_value, dict) or set(match_value) != {"tags", "count"}:
                raise ValueError(
                    f"{field}.minimum_required_tag_matches must contain only tags and count"
                )
            match_tags = _tag_values(
                match_value.get("tags"), f"{field}.minimum_required_tag_matches.tags", 1
            )
            match_count = _positive_int(
                match_value.get("count"),
                f"{field}.minimum_required_tag_matches.count",
                len(match_tags),
            )
            minimum_matches = MinimumRequiredTagMatches(match_tags, match_count)
        section_rules.append(
            TagListSection(
                section=section_name,
                min_tags=min_tags,
                max_tags=max_tags,
                required_tags=required_tags,
                minimum_required_tag_matches=minimum_matches,
            )
        )
    for field in ("ascii_only", "reject_duplicates", "reject_cross_section_duplicates"):
        if field in value and not isinstance(value[field], bool):
            raise ValueError(f"tag_lists.{field} must be a boolean")
    return TagListRules(
        sections=tuple(section_rules),
        ascii_only=value.get("ascii_only", False),
        reject_duplicates=value.get("reject_duplicates", False),
        reject_cross_section_duplicates=value.get("reject_cross_section_duplicates", False),
    )


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
    tag_lists: TagListRules | None = None

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
        required_sections = tuple(item.strip() for item in sections_value)
        return cls(
            name=name,
            format_version=format_version,
            required_sections=required_sections,
            min_output_chars=min_chars,
            max_output_chars=max_chars,
            forbidden_substrings=forbidden_substrings,
            reference_pattern=reference_pattern,
            reference_index_base=index_base,
            require_all_attachments_referenced=bool(
                value.get("require_all_attachments_referenced", False)
            ),
            tag_lists=_tag_list_rules(value.get("tag_lists"), required_sections),
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
    heading_matches = list(SECTION_PATTERN.finditer(text))
    discovered = tuple((match.group(1) or match.group(2)).strip() for match in heading_matches)
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

    tag_section_counts: dict[str, int] = {}
    if contract.tag_lists:
        normalized_tag_lists: dict[str, set[str]] = {}
        for tag_rule in contract.tag_lists.sections:
            matching_positions = [
                index
                for index, section in enumerate(discovered)
                if section.casefold() == tag_rule.section.casefold()
            ]
            if len(matching_positions) != 1:
                issues.append(
                    ValidationIssue(
                        "TAG_LIST_SECTION_UNAVAILABLE",
                        f"Tag-list section must appear exactly once: {tag_rule.section}",
                    )
                )
                continue
            position = matching_positions[0]
            start = heading_matches[position].end()
            end = (
                heading_matches[position + 1].start()
                if position + 1 < len(heading_matches)
                else len(text)
            )
            contents = text[start:end].strip()
            flattened = re.sub(r"\s*\r?\n\s*", " ", contents)
            raw_tags = flattened.split(",") if flattened else []
            if not raw_tags or not any(tag.strip() for tag in raw_tags):
                issues.append(
                    ValidationIssue(
                        "TAG_LIST_EMPTY", f"Tag-list section is empty: {tag_rule.section}"
                    )
                )
                tag_section_counts[tag_rule.section] = 0
                continue
            if any(not tag.strip() for tag in raw_tags):
                issues.append(
                    ValidationIssue(
                        "TAG_LIST_EMPTY_ITEM",
                        "Tag-list section contains an empty comma-delimited item: "
                        f"{tag_rule.section}",
                    )
                )
            tags = [tag.strip() for tag in raw_tags if tag.strip()]
            normalized_tags = [_normalize_tag(tag) for tag in tags]
            tag_section_counts[tag_rule.section] = len(tags)
            normalized_tag_lists[tag_rule.section] = set(normalized_tags)
            if contract.tag_lists.ascii_only and any(not tag.isascii() for tag in tags):
                issues.append(
                    ValidationIssue(
                        "TAG_LIST_NON_ASCII",
                        f"Tag-list section contains non-ASCII text: {tag_rule.section}",
                    )
                )
            if contract.tag_lists.reject_duplicates and len(set(normalized_tags)) != len(
                normalized_tags
            ):
                issues.append(
                    ValidationIssue(
                        "TAG_LIST_DUPLICATE",
                        f"Tag-list section contains duplicate normalized tags: {tag_rule.section}",
                    )
                )
            if len(tags) < tag_rule.min_tags:
                issues.append(
                    ValidationIssue(
                        "TAG_LIST_TOO_SHORT",
                        f"Tag-list section needs at least {tag_rule.min_tags} tags: "
                        f"{tag_rule.section}",
                    )
                )
            if tag_rule.max_tags is not None and len(tags) > tag_rule.max_tags:
                issues.append(
                    ValidationIssue(
                        "TAG_LIST_TOO_LONG",
                        f"Tag-list section allows at most {tag_rule.max_tags} tags: "
                        f"{tag_rule.section}",
                    )
                )
            missing_required = set(tag_rule.required_tags).difference(
                normalized_tag_lists[tag_rule.section]
            )
            if missing_required:
                issues.append(
                    ValidationIssue(
                        "TAG_LIST_MISSING_REQUIRED",
                        f"Tag-list section is missing {len(missing_required)} required tag(s): "
                        f"{tag_rule.section}",
                    )
                )
            if tag_rule.minimum_required_tag_matches:
                match_count = len(
                    normalized_tag_lists[tag_rule.section].intersection(
                        tag_rule.minimum_required_tag_matches.tags
                    )
                )
                if match_count < tag_rule.minimum_required_tag_matches.count:
                    issues.append(
                        ValidationIssue(
                            "TAG_LIST_INSUFFICIENT_BASELINE",
                            f"Tag-list section needs at least "
                            f"{tag_rule.minimum_required_tag_matches.count} configured baseline "
                            f"tags: {tag_rule.section}",
                        )
                    )
        if contract.tag_lists.reject_cross_section_duplicates:
            names = list(normalized_tag_lists)
            for left_index, left_name in enumerate(names):
                for right_name in names[left_index + 1 :]:
                    if normalized_tag_lists[left_name].intersection(
                        normalized_tag_lists[right_name]
                    ):
                        issues.append(
                            ValidationIssue(
                                "TAG_LIST_CROSS_SECTION_DUPLICATE",
                                "A normalized tag appears in more than one configured tag-list "
                                "section.",
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
            "tag_section_counts": tag_section_counts,
        },
    )
