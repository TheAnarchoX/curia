"""Minimal smoke tests to keep CI green while the codebase is being bootstrapped."""

from curia_connectors_eerstekamer.connector import EersteKamerConnector
from curia_connectors_ibabs.config import IbabsSourceConfig
from curia_connectors_ibabs.connector import IbabsConnector
from curia_connectors_kiesraad.connector import KiesraadConnector
from curia_connectors_ori.connector import OpenRaadsinformatieConnector
from curia_connectors_tweedekamer.connector import TweedeKamerConnector
from curia_connectors_woogle.connector import WoogleConnector

from apps.api.app.main import create_app


def test_create_app_builds_fastapi_application() -> None:
    """The API application should build successfully."""
    app = create_app()
    assert app.title == "Curia API"


def test_connector_metadata_smoke() -> None:
    """Connector stubs should be importable and expose metadata."""
    ibabs = IbabsConnector(
        IbabsSourceConfig(
            base_url="https://example.ibabs.eu",
            municipality_slug="example-town",
        )
    )

    connectors = [
        ibabs,
        TweedeKamerConnector(),
        OpenRaadsinformatieConnector(),
        KiesraadConnector(),
        WoogleConnector(),
        EersteKamerConnector(),
    ]

    source_types = {connector.get_meta().source_type for connector in connectors}
    assert source_types == {
        "ibabs",
        "tweedekamer",
        "openraadsinformatie",
        "kiesraad",
        "woogle",
        "eerstekamer",
    }
