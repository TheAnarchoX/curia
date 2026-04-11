"""Source connector registry."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from curia_ingestion.interfaces import SourceConnector

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Registry that maps source_type strings to connector factories."""

    def __init__(self) -> None:
        """Initialize an empty connector registry."""
        self._connectors: dict[str, Callable[[], SourceConnector]] = {}

    @staticmethod
    def _get_connector_name(connector: object) -> str:
        """Return a readable name for a connector instance or factory."""
        return getattr(connector, "__name__", connector.__class__.__name__)

    def register(
        self,
        connector: SourceConnector | Callable[[], SourceConnector],
    ) -> SourceConnector | Callable[[], SourceConnector]:
        """Register a connector instance or factory.

        Factory callables are invoked once at registration time so the registry
        can read connector metadata and determine the ``source_type`` key.
        """
        from curia_ingestion.interfaces import SourceConnector as _SC

        if isinstance(connector, _SC):
            instance = connector

            def factory() -> SourceConnector:
                return instance

            connector_name = self._get_connector_name(connector)
        elif callable(connector):
            factory = connector
            instance = factory()
            connector_name = self._get_connector_name(connector)
            if not isinstance(instance, _SC):
                raise TypeError(f"{connector!r} did not produce a SourceConnector instance")
        else:
            raise TypeError(f"{connector!r} is not a SourceConnector instance or factory")

        meta = instance.get_meta()
        source_type = meta.source_type
        if source_type in self._connectors:
            logger.warning(
                "Overwriting connector for source_type=%s (old=%s, new=%s)",
                source_type,
                self._get_connector_name(self._connectors[source_type]),
                connector_name,
            )
        self._connectors[source_type] = factory
        logger.info("Registered connector %s for source_type=%s", connector_name, source_type)
        return connector

    def get(self, source_type: str) -> Callable[[], SourceConnector]:
        """Return the connector factory registered for *source_type*."""
        try:
            return self._connectors[source_type]
        except KeyError:
            raise KeyError(
                f"No connector registered for source_type={source_type!r}. Available: {sorted(self._connectors)}"
            ) from None

    def list_registered(self) -> list[str]:
        """Return sorted list of registered source type keys."""
        return sorted(self._connectors)
