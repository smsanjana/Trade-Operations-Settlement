"""Content-addressed evidence storage with role-scoped retrieval and retention metadata.

Enforces immutability, SHA-256 content verification, and role-based access to sensitive evidence.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvidenceAccessError(Exception):
    """Raised when an actor lacks the required role to access restricted evidence content."""


@dataclass
class ArtifactMetadata:
    source_name: str
    media_type: str
    retention_class: str
    region: str
    trust_classification: str = "untrusted"
    legal_hold: bool = False
    captured_at: datetime = field(default_factory=utc_now)


@dataclass
class ArtifactReference:
    artifact_id: str
    content_hash: str
    metadata: ArtifactMetadata


class EvidenceStore:
    """Content-addressed evidence store maintaining immutable artifacts and metadata."""

    from typing import ClassVar

    CONTENT_AUTHORIZED_ROLES: ClassVar[set[str]] = {
        "settlement_analyst",
        "corporate_actions_analyst",
        "approver",
        "supervisor",
        "system",
    }

    def __init__(self) -> None:
        self._content: dict[str, bytes] = {}  # artifact_id -> raw content
        self._metadata: dict[str, ArtifactMetadata] = {}  # artifact_id -> metadata
        self._hashes: dict[str, str] = {}  # artifact_id -> sha256

    def put_artifact(
        self,
        content: bytes,
        metadata: ArtifactMetadata,
        artifact_id: str | None = None,
    ) -> ArtifactReference:
        if artifact_id and artifact_id in self._content:
            raise ValueError(f"Artifact {artifact_id} already exists and is immutable")

        target_id = artifact_id or f"EVD-{uuid.uuid4().hex[:12]}"
        content_hash = hashlib.sha256(content).hexdigest()

        self._content[target_id] = content
        self._metadata[target_id] = metadata
        self._hashes[target_id] = content_hash

        return ArtifactReference(
            artifact_id=target_id,
            content_hash=content_hash,
            metadata=metadata,
        )

    def get_artifact_metadata(self, artifact_id: str) -> ArtifactMetadata:
        if artifact_id not in self._metadata:
            raise KeyError(f"Artifact {artifact_id} not found")
        return self._metadata[artifact_id]

    def get_artifact_content(self, artifact_id: str, required_role: str) -> bytes:
        if artifact_id not in self._content:
            raise KeyError(f"Artifact {artifact_id} not found")

        if required_role not in self.CONTENT_AUTHORIZED_ROLES:
            raise EvidenceAccessError(
                f"Role '{required_role}' is not authorized to read raw evidence content for {artifact_id}"
            )

        return self._content[artifact_id]

    def get_artifact_hash(self, artifact_id: str) -> str:
        if artifact_id not in self._hashes:
            raise KeyError(f"Artifact {artifact_id} not found")
        return self._hashes[artifact_id]
