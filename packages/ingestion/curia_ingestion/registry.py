"""Source connector registry."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from curia_ingestion.interfaces import SourceConnector

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Registry that maps source_type strings to SourceConnector classes."""

    def __init__(self) -> None:
        """Initialize an empty connector registry."""
        self._connectors: dict[str, type[SourceConnector]] = {}

    def register(self, connector_class: type[SourceConnector]) -> type[SourceConnector]:
        """Register a connector class. Can also be used as a decorator."""
        from curia_ingestion.interfaces import SourceConnector as _SC

        if not (isinstance(connector_class, type) and issubclass(connector_class, _SC)):
            raise TypeError(f"{connector_class!r} is not a SourceConnector subclass")

        meta = connector_class.get_meta(connector_class)  # type: ignore[arg-type]
        source_type = meta.source_type
        if source_type in self._connectors:
            logger.warning(
                "Overwriting connector for source_type=%s (old=%s, new=%s)",
                source_type,
                self._connectors[source_type].__name__,
                connector_class.__name__,
            )
        self._connectors[source_type] = connector_class
        logger.info("Registered connector %s for source_type=%s", connector_class.__name__, source_type)
        return connector_class

    def get(self, source_type: str) -> type[SourceConnector]:
        """Return the connector class registered for *source_type*."""
        try:
            return self._connectors[source_type]
        except KeyError:
            raise KeyError(
                f"No connector registered for source_type={source_type!r}. Available: {sorted(self._connectors)}"
            ) from None

    def list_registered(self) -> list[str]:
        """Return sorted list of registered source type keys."""
        return sorted(self._connectors)
