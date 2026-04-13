"""Reusable OData v4 client for the Tweede Kamer Gegevensmagazijn API."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import TypedDict, TypeVar, Unpack, cast
from urllib.parse import urljoin
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/"


class ODataEntity(BaseModel):
    """Base model for Tweede Kamer OData entities."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: UUID | None = Field(default=None, alias="Id")
    gewijzigd_op: datetime | None = Field(default=None, alias="GewijzigdOp")
    api_gewijzigd_op: datetime | None = Field(default=None, alias="ApiGewijzigdOp")
    verwijderd: bool | None = Field(default=None, alias="Verwijderd")
    odata_etag: str | None = Field(default=None, alias="@odata.etag")


class Persoon(ODataEntity):
    """Typed OData model for the Persoon entity set."""

    nummer: int | None = Field(default=None, alias="Nummer")
    initialen: str | None = Field(default=None, alias="Initialen")
    achternaam: str | None = Field(default=None, alias="Achternaam")
    voornamen: str | None = Field(default=None, alias="Voornamen")
    roepnaam: str | None = Field(default=None, alias="Roepnaam")
    functie: str | None = Field(default=None, alias="Functie")
    geboortedatum: date | None = Field(default=None, alias="Geboortedatum")
    fractielabel: str | None = Field(default=None, alias="Fractielabel")


class Fractie(ODataEntity):
    """Typed OData model for the Fractie entity set with shared OData fields only."""

    pass


class FractieZetel(ODataEntity):
    """Typed OData model for the FractieZetel entity set with shared OData fields only."""

    pass


class Commissie(ODataEntity):
    """Typed OData model for the Commissie entity set with shared OData fields only."""

    pass


class CommissieLid(ODataEntity):
    """Typed OData model for the CommissieLid entity set with shared OData fields only."""

    pass


class Vergadering(ODataEntity):
    """Typed OData model for the Vergadering entity set with shared OData fields only."""

    pass


class Zaak(ODataEntity):
    """Typed OData model for the Zaak entity set with shared OData fields only."""

    pass


class ZaakActor(ODataEntity):
    """Typed OData model for the ZaakActor entity set with shared OData fields only."""

    pass


class Document(ODataEntity):
    """Typed OData model for the Document entity set with shared OData fields only."""

    pass


class DocumentActor(ODataEntity):
    """Typed OData model for the DocumentActor entity set with shared OData fields only."""

    pass


class Stemming(ODataEntity):
    """Typed OData model for the Stemming entity set with shared OData fields only."""

    pass


class Besluit(ODataEntity):
    """Typed OData model for the Besluit entity set with shared OData fields only."""

    pass


class Agendapunt(ODataEntity):
    """Typed OData model for the Agendapunt entity set with shared OData fields only."""

    pass


class Activiteit(ODataEntity):
    """Typed OData model for the Activiteit entity set with shared OData fields only."""

    pass


class Kamerstukdossier(ODataEntity):
    """Typed OData model for the Kamerstukdossier entity set with shared OData fields only."""

    pass


ENTITY_SET_MODELS: dict[str, type[ODataEntity]] = {
    "Persoon": Persoon,
    "Fractie": Fractie,
    "FractieZetel": FractieZetel,
    "Commissie": Commissie,
    "CommissieLid": CommissieLid,
    "Vergadering": Vergadering,
    "Zaak": Zaak,
    "ZaakActor": ZaakActor,
    "Document": Document,
    "DocumentActor": DocumentActor,
    "Stemming": Stemming,
    "Besluit": Besluit,
    "Agendapunt": Agendapunt,
    "Activiteit": Activiteit,
    "Kamerstukdossier": Kamerstukdossier,
}

TEntity = TypeVar("TEntity", bound=ODataEntity)


class QueryOptions(TypedDict, total=False):
    """Supported OData query options."""

    filter: str | None
    select: str | Sequence[str] | None
    expand: str | Sequence[str] | None
    orderby: str | Sequence[str] | None
    top: int | None
    skip: int | None


class ODataClient:
    """Async OData v4 client with automatic pagination."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Initialize the client with an optional shared AsyncClient."""
        self._base_url = base_url.rstrip("/") + "/"
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout_seconds,
            headers={"Accept": "application/json"},
        )

    async def aclose(self) -> None:
        """Close the owned HTTP client."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> ODataClient:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Close the client when leaving the async context manager."""
        await self.aclose()

    async def fetch_entities(
        self,
        entity_set: str,
        *,
        model: type[TEntity] | None = None,
        filter: str | None = None,
        select: str | Sequence[str] | None = None,
        expand: str | Sequence[str] | None = None,
        orderby: str | Sequence[str] | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[TEntity]:
        """Fetch an entity set and follow any OData pagination links."""
        model_type = model or self._resolve_model(entity_set)
        params: dict[str, str] | None = self._build_query_params(
            filter=filter,
            select=select,
            expand=expand,
            orderby=orderby,
            top=top,
            skip=skip,
        )
        next_url: str | None = entity_set
        items: list[TEntity] = []

        while next_url is not None:
            response = await self._client.get(next_url, params=params)
            response.raise_for_status()
            payload = response.json()
            page_items = [
                cast(TEntity, model_type.model_validate(raw_item))
                for raw_item in payload.get("value", [])
            ]
            items.extend(page_items)
            next_link = payload.get("@odata.nextLink")
            if isinstance(next_link, str):
                if next_link.startswith(("http://", "https://")):
                    next_url = next_link
                else:
                    next_url = urljoin(self._base_url, next_link)
            else:
                next_url = None
            params = None

        return items

    async def list_persoon(self, **kwargs: Unpack[QueryOptions]) -> list[Persoon]:
        """Fetch Persoon entities."""
        return await self.fetch_entities("Persoon", model=Persoon, **kwargs)

    async def list_fractie(self, **kwargs: Unpack[QueryOptions]) -> list[Fractie]:
        """Fetch Fractie entities."""
        return await self.fetch_entities("Fractie", model=Fractie, **kwargs)

    async def list_fractiezetel(self, **kwargs: Unpack[QueryOptions]) -> list[FractieZetel]:
        """Fetch FractieZetel entities."""
        return await self.fetch_entities("FractieZetel", model=FractieZetel, **kwargs)

    async def list_commissie(self, **kwargs: Unpack[QueryOptions]) -> list[Commissie]:
        """Fetch Commissie entities."""
        return await self.fetch_entities("Commissie", model=Commissie, **kwargs)

    async def list_commissielid(self, **kwargs: Unpack[QueryOptions]) -> list[CommissieLid]:
        """Fetch CommissieLid entities."""
        return await self.fetch_entities("CommissieLid", model=CommissieLid, **kwargs)

    async def list_vergadering(self, **kwargs: Unpack[QueryOptions]) -> list[Vergadering]:
        """Fetch Vergadering entities."""
        return await self.fetch_entities("Vergadering", model=Vergadering, **kwargs)

    async def list_zaak(self, **kwargs: Unpack[QueryOptions]) -> list[Zaak]:
        """Fetch Zaak entities."""
        return await self.fetch_entities("Zaak", model=Zaak, **kwargs)

    async def list_zaakactor(self, **kwargs: Unpack[QueryOptions]) -> list[ZaakActor]:
        """Fetch ZaakActor entities."""
        return await self.fetch_entities("ZaakActor", model=ZaakActor, **kwargs)

    async def list_document(self, **kwargs: Unpack[QueryOptions]) -> list[Document]:
        """Fetch Document entities."""
        return await self.fetch_entities("Document", model=Document, **kwargs)

    async def list_documentactor(self, **kwargs: Unpack[QueryOptions]) -> list[DocumentActor]:
        """Fetch DocumentActor entities."""
        return await self.fetch_entities("DocumentActor", model=DocumentActor, **kwargs)

    async def list_stemming(self, **kwargs: Unpack[QueryOptions]) -> list[Stemming]:
        """Fetch Stemming entities."""
        return await self.fetch_entities("Stemming", model=Stemming, **kwargs)

    async def list_besluit(self, **kwargs: Unpack[QueryOptions]) -> list[Besluit]:
        """Fetch Besluit entities."""
        return await self.fetch_entities("Besluit", model=Besluit, **kwargs)

    async def list_agendapunt(self, **kwargs: Unpack[QueryOptions]) -> list[Agendapunt]:
        """Fetch Agendapunt entities."""
        return await self.fetch_entities("Agendapunt", model=Agendapunt, **kwargs)

    async def list_activiteit(self, **kwargs: Unpack[QueryOptions]) -> list[Activiteit]:
        """Fetch Activiteit entities."""
        return await self.fetch_entities("Activiteit", model=Activiteit, **kwargs)

    async def list_kamerstukdossier(self, **kwargs: Unpack[QueryOptions]) -> list[Kamerstukdossier]:
        """Fetch Kamerstukdossier entities."""
        return await self.fetch_entities("Kamerstukdossier", model=Kamerstukdossier, **kwargs)

    @staticmethod
    def _build_query_params(
        *,
        filter: str | None,
        select: str | Sequence[str] | None,
        expand: str | Sequence[str] | None,
        orderby: str | Sequence[str] | None,
        top: int | None,
        skip: int | None,
    ) -> dict[str, str]:
        """Build supported OData query parameters."""
        if top is not None and top < 0:
            msg = "$top must be greater than or equal to zero"
            raise ValueError(msg)
        if skip is not None and skip < 0:
            msg = "$skip must be greater than or equal to zero"
            raise ValueError(msg)

        params: dict[str, str] = {}
        if filter is not None:
            params["$filter"] = filter
        if select is not None:
            params["$select"] = ODataClient._normalise_list_param(select)
        if expand is not None:
            params["$expand"] = ODataClient._normalise_list_param(expand)
        if orderby is not None:
            params["$orderby"] = ODataClient._normalise_list_param(orderby)
        if top is not None:
            params["$top"] = str(top)
        if skip is not None:
            params["$skip"] = str(skip)
        return params

    @staticmethod
    def _normalise_list_param(value: str | Sequence[str]) -> str:
        """Convert sequence-based query options to the OData CSV form."""
        if isinstance(value, str):
            return value
        return ",".join(value)

    @staticmethod
    def _resolve_model(entity_set: str) -> type[ODataEntity]:
        """Resolve the default Pydantic model for a known entity set."""
        try:
            return ENTITY_SET_MODELS[entity_set]
        except KeyError as exc:
            msg = f"Unsupported Tweede Kamer entity set: {entity_set}"
            raise ValueError(msg) from exc


__all__ = [
    "Agendapunt",
    "Activiteit",
    "Besluit",
    "Commissie",
    "CommissieLid",
    "DEFAULT_BASE_URL",
    "Document",
    "DocumentActor",
    "ENTITY_SET_MODELS",
    "Fractie",
    "FractieZetel",
    "Kamerstukdossier",
    "ODataClient",
    "ODataEntity",
    "Persoon",
    "QueryOptions",
    "Stemming",
    "Vergadering",
    "Zaak",
    "ZaakActor",
]
