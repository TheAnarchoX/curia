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
    """Typed OData model for the Fractie entity set."""

    nummer: int | None = Field(default=None, alias="Nummer")
    afkorting: str | None = Field(default=None, alias="Afkorting")
    naam_nl: str | None = Field(default=None, alias="NaamNL")
    naam_en: str | None = Field(default=None, alias="NaamEN")
    aantal_zetels: int | None = Field(default=None, alias="AantalZetels")
    aantal_stemmen: int | None = Field(default=None, alias="AantalStemmen")
    datum_actief: datetime | None = Field(default=None, alias="DatumActief")
    datum_inactief: datetime | None = Field(default=None, alias="DatumInactief")
    content_type: str | None = Field(default=None, alias="ContentType")
    content_length: int | None = Field(default=None, alias="ContentLength")


class FractieZetel(ODataEntity):
    """Typed OData model for the FractieZetel entity set."""

    gewicht: int | None = Field(default=None, alias="Gewicht")
    fractie_id: UUID | None = Field(default=None, alias="Fractie_Id")


class Commissie(ODataEntity):
    """Typed OData model for the Commissie entity set."""

    nummer: int | None = Field(default=None, alias="Nummer")
    soort: str | None = Field(default=None, alias="Soort")
    afkorting: str | None = Field(default=None, alias="Afkorting")
    naam_nl: str | None = Field(default=None, alias="NaamNL")
    naam_en: str | None = Field(default=None, alias="NaamEN")
    naam_web_nl: str | None = Field(default=None, alias="NaamWebNL")
    naam_web_en: str | None = Field(default=None, alias="NaamWebEN")
    inhoudsopgave: str | None = Field(default=None, alias="Inhoudsopgave")
    datum_actief: datetime | None = Field(default=None, alias="DatumActief")
    datum_inactief: datetime | None = Field(default=None, alias="DatumInactief")


class CommissieZetel(ODataEntity):
    """Typed OData model for the CommissieZetel entity set."""

    gewicht: int | None = Field(default=None, alias="Gewicht")
    commissie_id: UUID | None = Field(default=None, alias="Commissie_Id")


class Vergadering(ODataEntity):
    """Typed OData model for the Vergadering entity set."""

    soort: str | None = Field(default=None, alias="Soort")
    titel: str | None = Field(default=None, alias="Titel")
    zaal: str | None = Field(default=None, alias="Zaal")
    vergaderjaar: str | None = Field(default=None, alias="Vergaderjaar")
    vergadering_nummer: int | None = Field(default=None, alias="VergaderingNummer")
    datum: datetime | None = Field(default=None, alias="Datum")
    aanvangstijd: datetime | None = Field(default=None, alias="Aanvangstijd")
    sluiting: datetime | None = Field(default=None, alias="Sluiting")
    kamer: str | None = Field(default=None, alias="Kamer")


class Zaak(ODataEntity):
    """Typed OData model for the Zaak entity set."""

    nummer: str | None = Field(default=None, alias="Nummer")
    soort: str | None = Field(default=None, alias="Soort")
    titel: str | None = Field(default=None, alias="Titel")
    citeertitel: str | None = Field(default=None, alias="Citeertitel")
    alias: str | None = Field(default=None, alias="Alias")
    status: str | None = Field(default=None, alias="Status")
    onderwerp: str | None = Field(default=None, alias="Onderwerp")
    gestart_op: datetime | None = Field(default=None, alias="GestartOp")
    organisatie: str | None = Field(default=None, alias="Organisatie")
    grondslag_voorhang: str | None = Field(default=None, alias="Grondslagvoorhang")
    termijn: datetime | None = Field(default=None, alias="Termijn")
    vergaderjaar: str | None = Field(default=None, alias="Vergaderjaar")
    volgnummer: int | None = Field(default=None, alias="Volgnummer")
    huidige_behandelstatus: str | None = Field(default=None, alias="HuidigeBehandelstatus")
    afgedaan: bool | None = Field(default=None, alias="Afgedaan")
    groot_project: bool | None = Field(default=None, alias="GrootProject")
    kabinetsappreciatie: str | None = Field(default=None, alias="Kabinetsappreciatie")


class ZaakActor(ODataEntity):
    """Typed OData model for the ZaakActor entity set."""

    zaak_id: UUID | None = Field(default=None, alias="Zaak_Id")
    actor_naam: str | None = Field(default=None, alias="ActorNaam")
    actor_fractie: str | None = Field(default=None, alias="ActorFractie")
    actor_afkorting: str | None = Field(default=None, alias="ActorAfkorting")
    functie: str | None = Field(default=None, alias="Functie")
    relatie: str | None = Field(default=None, alias="Relatie")
    sid_actor: str | None = Field(default=None, alias="SidActor")
    persoon_id: UUID | None = Field(default=None, alias="Persoon_Id")
    fractie_id: UUID | None = Field(default=None, alias="Fractie_Id")
    commissie_id: UUID | None = Field(default=None, alias="Commissie_Id")


class Document(ODataEntity):
    """Typed OData model for the Document entity set."""

    soort: str | None = Field(default=None, alias="Soort")
    document_nummer: str | None = Field(default=None, alias="DocumentNummer")
    titel: str | None = Field(default=None, alias="Titel")
    onderwerp: str | None = Field(default=None, alias="Onderwerp")
    datum: datetime | None = Field(default=None, alias="Datum")
    vergaderjaar: str | None = Field(default=None, alias="Vergaderjaar")
    kamer: int | None = Field(default=None, alias="Kamer")
    volgnummer: int | None = Field(default=None, alias="Volgnummer")
    citeertitel: str | None = Field(default=None, alias="Citeertitel")
    alias: str | None = Field(default=None, alias="Alias")
    datum_registratie: datetime | None = Field(default=None, alias="DatumRegistratie")
    datum_ontvangst: datetime | None = Field(default=None, alias="DatumOntvangst")
    aanhangselnummer: str | None = Field(default=None, alias="Aanhangselnummer")
    kenmerk_afzender: str | None = Field(default=None, alias="KenmerkAfzender")
    organisatie: str | None = Field(default=None, alias="Organisatie")
    content_type: str | None = Field(default=None, alias="ContentType")
    content_length: int | None = Field(default=None, alias="ContentLength")
    huidige_document_versie_id: UUID | None = Field(default=None, alias="HuidigeDocumentVersie_Id")


class DocumentActor(ODataEntity):
    """Typed OData model for the DocumentActor entity set."""

    document_id: UUID | None = Field(default=None, alias="Document_Id")
    actor_naam: str | None = Field(default=None, alias="ActorNaam")
    actor_fractie: str | None = Field(default=None, alias="ActorFractie")
    functie: str | None = Field(default=None, alias="Functie")
    relatie: str | None = Field(default=None, alias="Relatie")
    sid_actor: str | None = Field(default=None, alias="SidActor")
    persoon_id: UUID | None = Field(default=None, alias="Persoon_Id")
    fractie_id: UUID | None = Field(default=None, alias="Fractie_Id")
    commissie_id: UUID | None = Field(default=None, alias="Commissie_Id")


class Stemming(ODataEntity):
    """Typed OData model for the Stemming entity set."""

    besluit_id: UUID | None = Field(default=None, alias="Besluit_Id")
    soort: str | None = Field(default=None, alias="Soort")
    fractie_grootte: int | None = Field(default=None, alias="FractieGrootte")
    actor_naam: str | None = Field(default=None, alias="ActorNaam")
    actor_fractie: str | None = Field(default=None, alias="ActorFractie")
    vergissing: bool | None = Field(default=None, alias="Vergissing")
    sid_actor_lid: str | None = Field(default=None, alias="SidActorLid")
    sid_actor_fractie: str | None = Field(default=None, alias="SidActorFractie")
    persoon_id: UUID | None = Field(default=None, alias="Persoon_Id")
    fractie_id: UUID | None = Field(default=None, alias="Fractie_Id")


class Besluit(ODataEntity):
    """Typed OData model for the Besluit entity set."""

    agendapunt_id: UUID | None = Field(default=None, alias="Agendapunt_Id")
    stemmings_soort: str | None = Field(default=None, alias="StemmingsSoort")
    besluit_soort: str | None = Field(default=None, alias="BesluitSoort")
    besluit_tekst: str | None = Field(default=None, alias="BesluitTekst")
    opmerking: str | None = Field(default=None, alias="Opmerking")
    status: str | None = Field(default=None, alias="Status")
    agendapunt_zaak_besluit_volgorde: int | None = Field(default=None, alias="AgendapuntZaakBesluitVolgorde")


class Agendapunt(ODataEntity):
    """Typed OData model for the Agendapunt entity set."""

    nummer: str | None = Field(default=None, alias="Nummer")
    onderwerp: str | None = Field(default=None, alias="Onderwerp")
    aanvangstijd: datetime | None = Field(default=None, alias="Aanvangstijd")
    eindtijd: datetime | None = Field(default=None, alias="Eindtijd")
    volgorde: int | None = Field(default=None, alias="Volgorde")
    rubriek: str | None = Field(default=None, alias="Rubriek")
    noot: str | None = Field(default=None, alias="Noot")
    status: str | None = Field(default=None, alias="Status")
    activiteit_id: UUID | None = Field(default=None, alias="Activiteit_Id")


class Activiteit(ODataEntity):
    """Typed OData model for the Activiteit entity set."""

    soort: str | None = Field(default=None, alias="Soort")
    nummer: str | None = Field(default=None, alias="Nummer")
    onderwerp: str | None = Field(default=None, alias="Onderwerp")
    datum_soort: str | None = Field(default=None, alias="DatumSoort")
    datum: datetime | None = Field(default=None, alias="Datum")
    aanvangstijd: datetime | None = Field(default=None, alias="Aanvangstijd")
    eindtijd: datetime | None = Field(default=None, alias="Eindtijd")
    locatie: str | None = Field(default=None, alias="Locatie")
    besloten: bool | None = Field(default=None, alias="Besloten")
    status: str | None = Field(default=None, alias="Status")
    vergaderjaar: str | None = Field(default=None, alias="Vergaderjaar")
    kamer: str | None = Field(default=None, alias="Kamer")
    noot: str | None = Field(default=None, alias="Noot")
    vrs_nummer: str | None = Field(default=None, alias="VRSNummer")
    sid_voortouw: str | None = Field(default=None, alias="SidVoortouw")
    voortouw_naam: str | None = Field(default=None, alias="Voortouwnaam")
    voortouw_afkorting: str | None = Field(default=None, alias="Voortouwafkorting")
    voortouw_kortenaam: str | None = Field(default=None, alias="Voortouwkortenaam")
    voortouwcommissie_id: UUID | None = Field(default=None, alias="Voortouwcommissie_Id")
    aanvraagdatum: datetime | None = Field(default=None, alias="Aanvraagdatum")
    datum_verzoek_eerste_verlenging: datetime | None = Field(default=None, alias="DatumVerzoekEersteVerlenging")
    datum_mededeling_eerste_verlenging: datetime | None = Field(
        default=None,
        alias="DatumMededelingEersteVerlenging",
    )
    datum_verzoek_tweede_verlenging: datetime | None = Field(default=None, alias="DatumVerzoekTweedeVerlenging")
    datum_mededeling_tweede_verlenging: datetime | None = Field(
        default=None,
        alias="DatumMededelingTweedeVerlenging",
    )
    vervaldatum: datetime | None = Field(default=None, alias="Vervaldatum")


class Kamerstukdossier(ODataEntity):
    """Typed OData model for the Kamerstukdossier entity set."""

    titel: str | None = Field(default=None, alias="Titel")
    citeertitel: str | None = Field(default=None, alias="Citeertitel")
    alias: str | None = Field(default=None, alias="Alias")
    nummer: int | None = Field(default=None, alias="Nummer")
    toevoeging: str | None = Field(default=None, alias="Toevoeging")
    hoogste_volgnummer: int | None = Field(default=None, alias="HoogsteVolgnummer")
    afgesloten: bool | None = Field(default=None, alias="Afgesloten")
    kamer: str | None = Field(default=None, alias="Kamer")


ENTITY_SET_MODELS: dict[str, type[ODataEntity]] = {
    "Persoon": Persoon,
    "Fractie": Fractie,
    "FractieZetel": FractieZetel,
    "Commissie": Commissie,
    "CommissieZetel": CommissieZetel,
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
            page_items = [cast(TEntity, model_type.model_validate(raw_item)) for raw_item in payload.get("value", [])]
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

    async def list_commissiezetel(self, **kwargs: Unpack[QueryOptions]) -> list[CommissieZetel]:
        """Fetch CommissieZetel entities."""
        return await self.fetch_entities("CommissieZetel", model=CommissieZetel, **kwargs)

    async def list_commissielid(self, **kwargs: Unpack[QueryOptions]) -> list[CommissieZetel]:
        """Fetch CommissieZetel entities via the older CommissieLid name."""
        return await self.list_commissiezetel(**kwargs)

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

# Backward compatibility alias for earlier client code that used CommissieLid.
CommissieLid = CommissieZetel


__all__ = [
    "Agendapunt",
    "Activiteit",
    "Besluit",
    "Commissie",
    "CommissieLid",
    "CommissieZetel",
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
