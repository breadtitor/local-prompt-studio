from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class GenerationResult:
    content: str
    reasoning: str = ""
    finish_reason: str | None = None
    model: str | None = None
    continuations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: Literal["error", "warning"] = "error"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ContractReport:
    valid: bool
    contract_name: str
    discovered_sections: tuple[str, ...] = ()
    issues: tuple[ValidationIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "contract_name": self.contract_name,
            "discovered_sections": list(self.discovered_sections),
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": self.metadata,
        }
