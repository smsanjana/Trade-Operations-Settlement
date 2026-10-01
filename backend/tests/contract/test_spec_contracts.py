"""Contract validation tests for OpenAPI 3.1 and AsyncAPI 2.6 specifications."""

from pathlib import Path

import yaml


def get_contracts_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    contracts_dir = repo_root / "specs" / "001-trade-operations-settlement" / "contracts"
    assert contracts_dir.is_dir(), f"Contracts directory not found: {contracts_dir}"
    return contracts_dir


def test_openapi_contract_parses_and_has_required_structure() -> None:
    contracts_dir = get_contracts_dir()
    openapi_file = contracts_dir / "openapi.yaml"
    assert openapi_file.is_file(), "openapi.yaml missing"

    with openapi_file.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    assert doc.get("openapi") == "3.1.0"
    assert "paths" in doc
    assert "components" in doc

    paths = doc["paths"]
    assert "/cases" in paths
    assert "/cases/{caseId}" in paths
    assert "/cases/{caseId}/evidence" in paths

    # Verify security context uses enterprise identity
    assert doc.get("security") == [{"enterpriseIdentity": []}]


def test_decision_contracts_prohibit_client_authored_approver_identity() -> None:
    contracts_dir = get_contracts_dir()
    openapi_file = contracts_dir / "openapi.yaml"

    with openapi_file.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    schemas = doc.get("components", {}).get("schemas", {})

    # Check DecisionCommand schemas if present
    for name, schema in schemas.items():
        if "decision" in name.lower() and "properties" in schema:
            assert "approver_id" not in schema["properties"], (
                f"Schema '{name}' must not accept client-authored 'approver_id'"
            )


def test_asyncapi_contract_parses_and_has_required_channels() -> None:
    contracts_dir = get_contracts_dir()
    asyncapi_file = contracts_dir / "events.asyncapi.yaml"
    assert asyncapi_file.is_file(), "events.asyncapi.yaml missing"

    with asyncapi_file.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    assert doc.get("asyncapi") == "2.6.0"
    channels = doc.get("channels", {})

    expected_channels = [
        "trade-operations.intake.v1",
        "trade-operations.case-events.v1",
        "trade-operations.posting-instructions.v1",
        "trade-operations.posting-results.v1",
    ]
    for ch in expected_channels:
        assert ch in channels, f"Missing required AsyncAPI channel: {ch}"


def test_posting_instruction_channel_is_segregated() -> None:
    contracts_dir = get_contracts_dir()
    asyncapi_file = contracts_dir / "events.asyncapi.yaml"

    with asyncapi_file.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    posting_ch = doc["channels"]["trade-operations.posting-instructions.v1"]
    subscribe_op = posting_ch.get("subscribe", {})
    description = subscribe_op.get("description", "").lower()
    assert "separately privileged" in description or "posting service" in description
