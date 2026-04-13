"""Smoke tests for core package bootstrap paths."""

from __future__ import annotations

from curia_domain.enums import GoverningBodyType, InstitutionType, JurisdictionLevel, MeetingStatus
from curia_domain.models import GoverningBody, Institution, Jurisdiction, Meeting, Party, Politician
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


def test_create_app_builds_fastapi_application(api_app: FastAPI) -> None:
    """The API application should build successfully."""
    route_paths = {route.path for route in api_app.routes if isinstance(route, APIRoute)}

    assert api_app.title == "Curia API"
    assert api_app.debug is True
    assert "/health" in route_paths
    assert any(route_path.startswith("/api/v1/") for route_path in route_paths)


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
