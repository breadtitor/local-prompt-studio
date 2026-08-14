from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from .contracts import PromptContract

ALLOWED_TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml"}
MAX_FILE_BYTES = 512 * 1024
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
MAX_INCLUDED_FILES = 64


@dataclass(frozen=True)
class SkillPackage:
    name: str
    source: str
    prompt_text: str
    included_files: tuple[str, ...]
    contract: PromptContract | None = None
    warnings: tuple[str, ...] = ()


class SkillReader(Protocol):
    def exists(self, relative_path: str) -> bool: ...

    def read_text(self, relative_path: str) -> str: ...

    def list_reference_files(self) -> list[str]: ...


def _safe_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Skill package path is not safely relative: {value!r}")
    return str(path)


class DirectorySkillReader:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _resolve(self, relative_path: str) -> Path:
        path = (self.root / _safe_relative_path(relative_path)).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError(f"Skill path escapes its package: {relative_path}")
        return path

    def exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).is_file()

    def read_text(self, relative_path: str) -> str:
        path = self._resolve(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"Skill file was not found: {relative_path}")
        if path.suffix.lower() not in ALLOWED_TEXT_SUFFIXES:
            raise ValueError(f"Skill file type is not allowed: {relative_path}")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"Skill file is too large: {relative_path}")
        return path.read_text(encoding="utf-8")

    def list_reference_files(self) -> list[str]:
        reference_root = self.root / "references"
        if not reference_root.is_dir():
            return []
        return sorted(
            path.relative_to(self.root).as_posix()
            for path in reference_root.rglob("*")
            if path.is_file() and path.suffix.lower() in ALLOWED_TEXT_SUFFIXES
        )


class ZipSkillReader:
    def __init__(self, archive_path: Path):
        self.archive_path = archive_path.resolve()
        self.archive = zipfile.ZipFile(self.archive_path)
        safe_files: list[str] = []
        for info in self.archive.infolist():
            if info.is_dir():
                continue
            safe_files.append(_safe_relative_path(info.filename))
        entrypoints = sorted(
            (name for name in safe_files if PurePosixPath(name).name.casefold() == "skill.md"),
            key=lambda value: (len(PurePosixPath(value).parts), value),
        )
        if not entrypoints:
            self.archive.close()
            raise ValueError("ZIP skill package does not contain SKILL.md")
        entrypoint = PurePosixPath(entrypoints[0])
        self.prefix = entrypoint.parent
        self.files = {
            str(PurePosixPath(name).relative_to(self.prefix))
            for name in safe_files
            if PurePosixPath(name).is_relative_to(self.prefix)
        }

    def close(self) -> None:
        self.archive.close()

    def _archive_name(self, relative_path: str) -> str:
        safe = PurePosixPath(_safe_relative_path(relative_path))
        return str(self.prefix / safe)

    def exists(self, relative_path: str) -> bool:
        return _safe_relative_path(relative_path) in self.files

    def read_text(self, relative_path: str) -> str:
        safe = _safe_relative_path(relative_path)
        if safe not in self.files:
            raise FileNotFoundError(f"Skill file was not found: {relative_path}")
        if PurePosixPath(safe).suffix.lower() not in ALLOWED_TEXT_SUFFIXES:
            raise ValueError(f"Skill file type is not allowed: {relative_path}")
        info = self.archive.getinfo(self._archive_name(safe))
        if info.file_size > MAX_FILE_BYTES:
            raise ValueError(f"Skill file is too large: {relative_path}")
        return self.archive.read(info).decode("utf-8")

    def list_reference_files(self) -> list[str]:
        return sorted(
            name
            for name in self.files
            if name.startswith("references/")
            and PurePosixPath(name).suffix.lower() in ALLOWED_TEXT_SUFFIXES
        )


def _parse_manifest(reader: SkillReader) -> dict[str, Any]:
    if not reader.exists("skill.json"):
        return {}
    value = json.loads(reader.read_text("skill.json"))
    if not isinstance(value, dict):
        raise ValueError("skill.json must contain an object")
    return value


def _frontmatter_name(skill_text: str) -> str | None:
    if not skill_text.startswith("---"):
        return None
    closing = skill_text.find("\n---", 3)
    if closing < 0:
        return None
    match = re.search(r"(?m)^name\s*:\s*[\"']?([^\n\"']+)", skill_text[3:closing])
    return match.group(1).strip() if match else None


def _load_from_reader(reader: SkillReader, source: str) -> SkillPackage:
    manifest = _parse_manifest(reader)
    entrypoint = _safe_relative_path(str(manifest.get("entrypoint", "SKILL.md")))
    skill_text = reader.read_text(entrypoint).strip()
    if not skill_text:
        raise ValueError("SKILL.md must not be empty")

    include_value = manifest.get("include")
    if include_value is None:
        included = reader.list_reference_files()
    else:
        if not isinstance(include_value, list) or not all(
            isinstance(item, str) for item in include_value
        ):
            raise ValueError("skill.json include must be an array of relative paths")
        included = [_safe_relative_path(item) for item in include_value]
    included = list(dict.fromkeys(included))
    if len(included) > MAX_INCLUDED_FILES:
        raise ValueError(f"Skill package includes more than {MAX_INCLUDED_FILES} reference files")

    chunks = [f"# Skill entrypoint: {entrypoint}\n\n{skill_text}"]
    total_bytes = len(skill_text.encode("utf-8"))
    for relative_path in included:
        reference_text = reader.read_text(relative_path).strip()
        total_bytes += len(reference_text.encode("utf-8"))
        if total_bytes > MAX_PACKAGE_BYTES:
            raise ValueError(f"Skill package exceeds {MAX_PACKAGE_BYTES} bytes of text")
        chunks.append(f"# Skill reference: {relative_path}\n\n{reference_text}")

    contract_path_value = manifest.get("contract")
    if contract_path_value is None and reader.exists("contract.json"):
        contract_path_value = "contract.json"
    contract = None
    if contract_path_value is not None:
        contract_path = _safe_relative_path(str(contract_path_value))
        contract_value = json.loads(reader.read_text(contract_path))
        if not isinstance(contract_value, dict):
            raise ValueError("contract JSON must contain an object")
        contract = PromptContract.from_dict(contract_value)

    name = str(
        manifest.get("name") or _frontmatter_name(skill_text) or "Local prompt skill"
    ).strip()
    warnings: list[str] = []
    if not manifest:
        warnings.append(
            "No skill.json manifest was found; all supported text files "
            "under references/ were loaded."
        )
    return SkillPackage(
        name=name,
        source=source,
        prompt_text="\n\n".join(chunks),
        included_files=(entrypoint, *included),
        contract=contract,
        warnings=tuple(warnings),
    )


def load_skill_package(path: str | Path) -> SkillPackage:
    source_path = Path(path).expanduser().resolve()
    if source_path.is_dir():
        return _load_from_reader(DirectorySkillReader(source_path), str(source_path))
    if source_path.is_file() and source_path.name.casefold() == "skill.md":
        return _load_from_reader(DirectorySkillReader(source_path.parent), str(source_path.parent))
    if source_path.is_file() and source_path.suffix.casefold() == ".zip":
        reader = ZipSkillReader(source_path)
        try:
            return _load_from_reader(reader, str(source_path))
        finally:
            reader.close()
    raise ValueError("Select a skill directory, a SKILL.md file, or a ZIP skill package.")
