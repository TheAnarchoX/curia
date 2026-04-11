"""iBabs connector for the Curia ingestion pipeline."""

from curia_connectors_ibabs.config import IbabsSourceConfig
from curia_connectors_ibabs.connector import IbabsConnector

__all__ = ["IbabsConnector", "IbabsSourceConfig"]
