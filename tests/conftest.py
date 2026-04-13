"""Shared fixtures for smoke tests."""

import pytest
from curia_connectors_eerstekamer.connector import EersteKamerConnector
from curia_connectors_ibabs.config import IbabsSourceConfig
from curia_connectors_ibabs.connector import IbabsConnector
from curia_connectors_kiesraad.connector import KiesraadConnector
from curia_connectors_ori.connector import OpenRaadsinformatieConnector
from curia_connectors_tweedekamer.connector import TweedeKamerConnector
from curia_connectors_woogle.connector import WoogleConnector
from curia_ingestion.interfaces import SourceConnector
from fastapi import FastAPI

from apps.api.app.config import Settings
from apps.api.app.main import create_app


@pytest.fixture
def app_settings() -> Settings:
    """Return deterministic settings for app smoke tests."""
    return Settings.model_validate(
        {
            "debug": True,
            "cors_origins": ["http://localhost:3000", "https://example.com"],
        }
    )


@pytest.fixture
def api_app(app_settings: Settings) -> FastAPI:
    """Build a FastAPI app without relying on environment state."""
    return create_app(app_settings)


@pytest.fixture
def ibabs_source_config() -> IbabsSourceConfig:
    """Return a minimal iBabs source configuration for smoke tests."""
    return IbabsSourceConfig(
        base_url="https://example.ibabs.eu",
        municipality_slug="example-town",
    )


@pytest.fixture
def connector_instances(ibabs_source_config: IbabsSourceConfig) -> list[SourceConnector]:
    """Instantiate each built-in connector without external services."""
    return [
        IbabsConnector(ibabs_source_config),
        TweedeKamerConnector(),
        OpenRaadsinformatieConnector(),
        KiesraadConnector(),
        WoogleConnector(),
        EersteKamerConnector(),
    ]
