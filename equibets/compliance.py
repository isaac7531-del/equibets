"""Compliance gates for source ingestion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "source_compliance.json"


class SourceComplianceError(RuntimeError):
    """Raised when a source is not approved for the requested ingest job."""


@dataclass(frozen=True)
class SourceCompliancePolicy:
    source_id: str
    display_name: str
    base_url: str | None
    robots_url: str | None
    terms_url: str | None
    approved_for_ingest: bool
    raw_storage_allowed: bool
    allowed_job_types: tuple[str, ...]
    reviewed_at: str | None
    reviewed_by: str | None
    notes: str

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "SourceCompliancePolicy":
        return cls(
            source_id=_required_str(values, "source_id"),
            display_name=_required_str(values, "display_name"),
            base_url=_optional_str(values, "base_url"),
            robots_url=_optional_str(values, "robots_url"),
            terms_url=_optional_str(values, "terms_url"),
            approved_for_ingest=_required_bool(values, "approved_for_ingest"),
            raw_storage_allowed=_required_bool(values, "raw_storage_allowed"),
            allowed_job_types=_string_tuple(values, "allowed_job_types"),
            reviewed_at=_optional_str(values, "reviewed_at"),
            reviewed_by=_optional_str(values, "reviewed_by"),
            notes=_required_str(values, "notes"),
        )


def load_source_compliance(path: Path | str = DATA_FILE) -> dict[str, SourceCompliancePolicy]:
    with Path(path).open(encoding="utf-8") as compliance_file:
        payload = json.load(compliance_file)

    return {
        policy.source_id: policy
        for policy in (SourceCompliancePolicy.from_mapping(item) for item in payload.get("sources", []))
    }


def require_source_approval(
    source_id: str,
    job_type: str,
    *,
    path: Path | str = DATA_FILE,
) -> SourceCompliancePolicy:
    """Return the policy only when the source is approved for this job type."""

    policies = load_source_compliance(path)
    policy = policies.get(source_id)
    if policy is None:
        raise SourceComplianceError(f"{source_id} is missing from source compliance policy")
    if not policy.approved_for_ingest:
        raise SourceComplianceError(
            f"{source_id} is not approved for automated ingest. Review terms/robots/licence before running {job_type}."
        )
    if job_type not in policy.allowed_job_types:
        allowed = ", ".join(policy.allowed_job_types) or "none"
        raise SourceComplianceError(f"{source_id} is not approved for {job_type}; allowed job types: {allowed}")
    return policy


def _required_str(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_str(values: dict[str, object], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be null or a non-empty string")
    return value


def _required_bool(values: dict[str, object], key: str) -> bool:
    value = values.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list of strings")
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{key} must contain only non-empty strings")
    return tuple(value)
