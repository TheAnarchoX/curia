"""Smoke tests for core package bootstrap paths."""

from __future__ import annotations

from datetime import date

from curia_domain import (
    BillCreate,
    BillResponse,
    BillStageCreate,
    BillStageResponse,
    BillType,
    Election,
    ElectionResult,
    ElectionType,
    GoverningBody,
    GoverningBodyType,
    Institution,
    InstitutionType,
    Jurisdiction,
    JurisdictionLevel,
    Meeting,
    MeetingStatus,
    Party,
    Politician,
)
from curia_ingestion.interfaces import SourceConnector
from fastapi import FastAPI
from fastapi.routing import APIRoute


def test_domain_models_can_be_created() -> None:
    """Core Pydantic domain models should build with minimal valid data."""
    jurisdiction = Jurisdiction(
        name="Amsterdam",
        level=JurisdictionLevel.MUNICIPALITY,
    )
    institution = Institution(
        jurisdiction_id=jurisdiction.id,
        name="Gemeenteraad Amsterdam",
        slug="gemeenteraad-amsterdam",
        institution_type=InstitutionType.COUNCIL,
    )
    governing_body = GoverningBody(
        institution_id=institution.id,
        name="Raad",
        body_type=GoverningBodyType.COUNCIL,
    )
    meeting = Meeting(
        governing_body_id=governing_body.id,
        title="Raadsvergadering",
    )
    party = Party(name="Voorbeeldpartij")
    politician = Politician(full_name="Jane Doe")

    assert meeting.status is MeetingStatus.SCHEDULED
    assert party.aliases == []
    assert politician.full_name == "Jane Doe"


def test_national_domain_models_can_be_created() -> None:
    """National-level bill and election models should build with valid data."""
    bill_create = BillCreate(
        title="Wet open overheid",
        bill_type=BillType.GOVERNMENT,
    )
    bill_response = BillResponse(
        title="Wet open overheid",
        bill_type=BillType.GOVERNMENT,
    )
    bill_stage_create = BillStageCreate(
        bill_id=bill_response.id,
        stage_name="introduced",
    )
    bill_stage_response = BillStageResponse(
        bill_id=bill_response.id,
        stage_name="introduced",
    )
    election = Election(
        name="Tweede Kamerverkiezing 2025",
        election_type=ElectionType.PARLIAMENTARY,
        election_date=date(2025, 10, 29),
    )
    election_result = ElectionResult(
        election_id=election.id,
        votes=12345,
        seats=10,
    )

    assert bill_create.bill_type is BillType.GOVERNMENT
    assert "id" not in bill_create.model_dump()
    assert bill_response.status.value == "introduced"
    assert bill_stage_create.stage_name == "introduced"
    assert "id" not in bill_stage_create.model_dump()
    assert bill_stage_response.bill_id == bill_response.id
    assert election.election_type is ElectionType.PARLIAMENTARY
    assert election_result.seats == 10


def test_create_app_builds_fastapi_application(api_app: FastAPI) -> None:
    """The API application should build successfully."""
    api_route_paths = {route.path for route in api_app.routes if isinstance(route, APIRoute)}

    assert api_app.title == "Curia API"
    assert api_app.debug is True
    assert "/health" in api_route_paths
    assert any(route_path.startswith("/api/v1/") for route_path in api_route_paths)


def test_connector_metadata_smoke(connector_instances: list[SourceConnector]) -> None:
    """Connector implementations should instantiate and expose metadata."""
    source_types = {connector.get_meta().source_type for connector in connector_instances}

    assert source_types == {
        "ibabs",
        "tweedekamer",
        "openraadsinformatie",
        "kiesraad",
        "woogle",
        "eerstekamer",
    }
