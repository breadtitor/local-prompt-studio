"""Local Prompt Studio public API."""

from .client import OpenAICompatibleClient, StudioSettings
from .contracts import PromptContract, validate_output
from .models import ContractReport, GenerationResult, ValidationIssue

__all__ = [
    "ContractReport",
    "GenerationResult",
    "OpenAICompatibleClient",
    "PromptContract",
    "StudioSettings",
    "ValidationIssue",
    "validate_output",
]

__version__ = "0.1.0"
