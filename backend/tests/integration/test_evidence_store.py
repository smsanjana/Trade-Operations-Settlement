"""Tests for content-addressed evidence storage, role-scoped retrieval, and retention."""

import pytest

from trade_operations_settlement.application.tools.evidence_store import (
    ArtifactMetadata,
    EvidenceAccessError,
    EvidenceStore,
)


def test_evidence_content_hashing_and_retrieval() -> None:
    store = EvidenceStore()
    content = b"Trader Chat: Agreed settlement fee is 450.00 USD on 2026-09-22"
    metadata = ArtifactMetadata(
        source_name="bloomberg_chat",
        media_type="text/plain",
        retention_class="7_year_audit",
        region="eu-west-1",
    )

    artifact_ref = store.put_artifact(content, metadata)
    assert artifact_ref.content_hash is not None
    assert len(artifact_ref.content_hash) == 64  # SHA-256 hex string

    retrieved = store.get_artifact_content(artifact_ref.artifact_id, required_role="settlement_analyst")
    assert retrieved == content


def test_role_scoped_evidence_access_withholds_body_when_unauthorized() -> None:
    store = EvidenceStore()
    content = b"Confidential Contract Note with counterparty details"
    metadata = ArtifactMetadata(
        source_name="contract_note_pdf",
        media_type="application/pdf",
        retention_class="7_year_audit",
        region="us-east-1",
    )
    artifact_ref = store.put_artifact(content, metadata)

    # Auditor with metadata-only role can access metadata
    meta = store.get_artifact_metadata(artifact_ref.artifact_id)
    assert meta.source_name == "contract_note_pdf"

    # But unauthorized role cannot read raw content
    with pytest.raises(EvidenceAccessError):
        store.get_artifact_content(artifact_ref.artifact_id, required_role="unauthorized_guest")


def test_immutability_of_stored_evidence() -> None:
    store = EvidenceStore()
    content = b"Original Swift MT548 status advice"
    metadata = ArtifactMetadata(
        source_name="swift_mt548",
        media_type="application/xml",
        retention_class="regulatory",
        region="us-east-1",
    )
    ref = store.put_artifact(content, metadata)

    # Attempting to overwrite existing artifact id must raise error
    with pytest.raises(ValueError, match="immutable"):
        store.put_artifact(b"Tampered content", metadata, artifact_id=ref.artifact_id)
