"""Tweede Kamer OData v4 connector — implements the SourceConnector interface.

The Tweede Kamer provides a rich OData v4 API at:
    https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/

Unlike scraping-based connectors (iBabs, Eerste Kamer), this connector
consumes a structured API and returns JSON directly.  No HTML parsing
is required.

Key entities:
    Persoon, Fractie, Commissie, Vergadering, Zaak, Document, Stemming,
    Activiteit, Kamerstukdossier, Besluit, Agendapunt
"""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from curia_domain.db.models import MandateRow, PartyRow, PoliticianRow
from curia_domain.enums import JurisdictionLevel, MandateRole
from curia_domain.models import Mandate, Party, Politician
from curia_ingestion.interfaces import (
    CrawlConfig,
    CrawlResult,
    SourceConnector,
    SourceConnectorMeta,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from curia_connectors_tweedekamer.odata_client import (
    Fractie,
    FractieZetelPersoon,
    ODataClient,
    Persoon,
)

_VERSION = "0.1.0"
_BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"

# OData entity sets we intend to synchronise
ENTITIES = (
    "Persoon",
    "Fractie",
    "FractieZetel",
    "Commissie",
    "CommissieZetel",
    "Vergadering",
    "Zaak",
    "ZaakActor",
    "Document",
    "DocumentActor",
    "Stemming",
    "Besluit",
    "Agendapunt",
    "Activiteit",
    "Kamerstukdossier",
)


@dataclass
class MemberPartySyncResult:
    """Outcome of syncing Tweede Kamer members, parties, and memberships."""

    created: int = 0
    existing: int = 0
    skipped: int = 0
    fetched_people: int = 0
    fetched_parties: int = 0
    fetched_memberships: int = 0

    @property
    def updated(self) -> int:
        """Deprecated alias for ``existing`` kept for backward compatibility."""
        return self.existing

    @updated.setter
    def updated(self, value: int) -> None:
        """Deprecated alias for ``existing`` kept for backward compatibility."""
        self.existing = value


class TweedeKamerConnector(SourceConnector):
    """Connector that synchronises data from the Tweede Kamer OData API."""

    def __init__(self) -> None:
        """Initialise the Tweede Kamer connector."""
        self._checkpoint: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # SourceConnector interface
    # ------------------------------------------------------------------

    def get_meta(self) -> SourceConnectorMeta:
        """Return connector metadata."""
        return SourceConnectorMeta(
            source_type="tweedekamer",
            name="Tweede Kamer der Staten-Generaal",
            version=_VERSION,
            description="Official OData v4 API for the Dutch House of Representatives",
            capabilities=[
                "members",
                "parties",
                "committees",
                "sessions",
                "bills",
                "documents",
                "votes",
                "motions",
                "amendments",
            ],
        )

    async def discover_pages(self, config: CrawlConfig) -> list[str]:
        """Build OData entity-set URLs to synchronise."""
        base = config.base_url or _BASE_URL
        return [f"{base.rstrip('/')}/{entity}" for entity in ENTITIES]

    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult:
        """Fetch a single OData entity-set page.

        .. note:: Stub — returns an empty result.  The real implementation
           will page through OData ``@odata.nextLink`` responses.
        """
        raise NotImplementedError(
            "TweedeKamerConnector.crawl_page is not yet implemented. "
            "See https://github.com/TheAnarchoX/Curia/issues for the tracking task."
        )

    async def get_checkpoint(self) -> dict[str, Any]:
        """Return the current sync checkpoint."""
        return dict(self._checkpoint)

    async def set_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """Persist a sync checkpoint."""
        self._checkpoint = dict(checkpoint)

    async def sync_members_and_parties(
        self,
        session: AsyncSession,
        *,
        institution_id: uuid.UUID,
        governing_body_id: uuid.UUID,
        odata_client: ODataClient | None = None,
    ) -> MemberPartySyncResult:
        """Fetch Tweede Kamer people, parties, and memberships and persist them."""
        manages_client = odata_client is None
        client = odata_client or ODataClient()
        result = MemberPartySyncResult()

        try:
            people, parties, seats = await asyncio.gather(
                client.list_persoon(),
                client.list_fractie(),
                client.list_fractiezetel(expand=["FractieZetelPersoon"]),
            )

            result.fetched_people = len(people)
            result.fetched_parties = len(parties)
            result.fetched_memberships = sum(len(seat.fractiezetel_persoon) for seat in seats if not seat.verwijderd)

            party_rows_by_id: dict[uuid.UUID, PartyRow] = {}
            politician_rows_by_id: dict[uuid.UUID, PoliticianRow] = {}
            parties_by_name = await self._load_existing_parties(session, parties)
            politicians_by_name = await self._load_existing_politicians(session, people)

            for party in parties:
                created, party_row = await self._upsert_party(
                    session,
                    party,
                    parties_by_name=parties_by_name,
                )
                if created is None or party_row is None:
                    result.skipped += 1
                    continue
                result.created += int(created)
                result.existing += int(not created)
                if party.id is not None:
                    party_rows_by_id[party.id] = party_row

            for person in people:
                created, politician_row = await self._upsert_politician(
                    session,
                    person,
                    politicians_by_name=politicians_by_name,
                )
                if created is None or politician_row is None:
                    result.skipped += 1
                    continue
                result.created += int(created)
                result.existing += int(not created)
                if person.id is not None:
                    politician_rows_by_id[person.id] = politician_row

            await session.flush()
            existing_mandates = await self._load_existing_mandates(
                session,
                party_rows_by_id=party_rows_by_id,
                politician_rows_by_id=politician_rows_by_id,
                institution_id=institution_id,
                governing_body_id=governing_body_id,
            )

            for seat in seats:
                if seat.verwijderd or seat.fractie_id is None:
                    continue
                membership_party_row = party_rows_by_id.get(seat.fractie_id)
                if membership_party_row is None:
                    result.skipped += len(seat.fractiezetel_persoon)
                    continue

                for membership in seat.fractiezetel_persoon:
                    created = await self._upsert_membership(
                        session,
                        membership=membership,
                        party_row=membership_party_row,
                        politician_rows_by_id=politician_rows_by_id,
                        existing_mandates=existing_mandates,
                        institution_id=institution_id,
                        governing_body_id=governing_body_id,
                    )
                    if created is None:
                        result.skipped += 1
                        continue
                    result.created += int(created)
                    result.existing += int(not created)

            await session.flush()
            return result
        finally:
            if manages_client:
                await client.aclose()

    @staticmethod
    def _build_politician(person: Persoon) -> Politician | None:
        given_name = person.roepnaam or person.voornamen
        family_name = (
            " ".join(part for part in (person.tussenvoegsel, person.achternaam) if part and part.strip()) or None
        )
        full_name = " ".join(part for part in (given_name, family_name) if part)

        if not full_name:
            return None

        return Politician(
            full_name=full_name,
            given_name=given_name,
            family_name=family_name,
            initials=person.initialen,
            gender=person.geslacht,
            date_of_birth=person.geboortedatum,
            notes=person.functie,
        )

    @staticmethod
    def _build_party(fractie: Fractie) -> Party | None:
        name = fractie.naam_nl or fractie.afkorting
        if not name:
            return None

        return Party(
            name=name,
            abbreviation=fractie.afkorting,
            scope_level=JurisdictionLevel.NATIONAL,
            active_from=TweedeKamerConnector._coerce_date(fractie.datum_actief),
            active_until=TweedeKamerConnector._coerce_date(fractie.datum_inactief),
        )

    @staticmethod
    def _build_mandate(
        membership: FractieZetelPersoon,
        *,
        politician_id: uuid.UUID,
        party_id: uuid.UUID,
        institution_id: uuid.UUID,
        governing_body_id: uuid.UUID,
    ) -> Mandate | None:
        if membership.verwijderd:
            return None

        return Mandate(
            politician_id=politician_id,
            party_id=party_id,
            institution_id=institution_id,
            governing_body_id=governing_body_id,
            role=TweedeKamerConnector._map_role(membership.functie),
            start_date=TweedeKamerConnector._coerce_date(membership.van),
            end_date=TweedeKamerConnector._coerce_date(membership.tot_en_met),
        )

    @staticmethod
    async def _upsert_party(
        session: AsyncSession,
        fractie: Fractie,
        *,
        parties_by_name: dict[str, PartyRow],
    ) -> tuple[bool | None, PartyRow | None]:
        party = TweedeKamerConnector._build_party(fractie)
        if party is None:
            return None, None

        row = parties_by_name.get(party.name)
        if row is None:
            row = PartyRow(
                name=party.name,
                abbreviation=party.abbreviation,
                scope_level=party.scope_level,
                active_from=party.active_from,
                active_until=party.active_until,
            )
            session.add(row)
            parties_by_name[party.name] = row
            return True, row

        row.abbreviation = party.abbreviation
        row.scope_level = party.scope_level
        row.active_from = party.active_from
        row.active_until = party.active_until
        return False, row

    @staticmethod
    async def _upsert_politician(
        session: AsyncSession,
        person: Persoon,
        *,
        politicians_by_name: dict[str, list[PoliticianRow]],
    ) -> tuple[bool | None, PoliticianRow | None]:
        politician = TweedeKamerConnector._build_politician(person)
        if politician is None:
            return None, None

        candidates = politicians_by_name.get(politician.full_name, [])

        row = next(
            (candidate for candidate in candidates if candidate.date_of_birth == politician.date_of_birth),
            None,
        )
        if (
            row is None
            and politician.date_of_birth is None
            and len(candidates) == 1
            and candidates[0].date_of_birth is None
        ):
            row = candidates[0]
        if row is None:
            row = PoliticianRow(
                full_name=politician.full_name,
                given_name=politician.given_name,
                family_name=politician.family_name,
                initials=politician.initials,
                gender=politician.gender,
                date_of_birth=politician.date_of_birth,
                notes=politician.notes,
            )
            session.add(row)
            politicians_by_name.setdefault(politician.full_name, []).append(row)
            return True, row

        row.given_name = politician.given_name
        row.family_name = politician.family_name
        row.initials = politician.initials
        row.gender = politician.gender
        row.date_of_birth = politician.date_of_birth
        row.notes = politician.notes
        return False, row

    @staticmethod
    async def _upsert_membership(
        session: AsyncSession,
        *,
        membership: FractieZetelPersoon,
        party_row: PartyRow,
        politician_rows_by_id: dict[uuid.UUID, PoliticianRow],
        existing_mandates: dict[
            tuple[uuid.UUID, uuid.UUID | None, uuid.UUID | None, uuid.UUID | None, str, date | None, date | None],
            MandateRow,
        ],
        institution_id: uuid.UUID,
        governing_body_id: uuid.UUID,
    ) -> bool | None:
        if membership.persoon_id is None:
            return None

        politician_row = politician_rows_by_id.get(membership.persoon_id)
        if politician_row is None:
            return None

        mandate = TweedeKamerConnector._build_mandate(
            membership,
            politician_id=politician_row.id,
            party_id=party_row.id,
            institution_id=institution_id,
            governing_body_id=governing_body_id,
        )
        if mandate is None:
            return None

        mandate_key = TweedeKamerConnector._mandate_key(
            politician_id=mandate.politician_id,
            party_id=mandate.party_id,
            institution_id=mandate.institution_id,
            governing_body_id=mandate.governing_body_id,
            role=mandate.role,
            start_date=mandate.start_date,
            end_date=mandate.end_date,
        )
        row = existing_mandates.get(mandate_key)
        if row is None:
            row = MandateRow(
                politician_id=mandate.politician_id,
                party_id=mandate.party_id,
                institution_id=mandate.institution_id,
                governing_body_id=mandate.governing_body_id,
                role=mandate.role,
                start_date=mandate.start_date,
                end_date=mandate.end_date,
            )
            session.add(row)
            existing_mandates[mandate_key] = row
            return True

        return False

    @staticmethod
    def _map_role(value: str | None) -> MandateRole:
        if not value:
            return MandateRole.MEMBER

        normalised = re.sub(r"[-\s]+", " ", value.strip().lower())
        tokens = set(normalised.split())
        if (
            "ondervoorzitter" in normalised
            or "vicevoorzitter" in normalised
            or ("vice" in tokens and "voorzitter" in tokens)
        ):
            return MandateRole.VICE_CHAIR
        if "voorzitter" in normalised:
            return MandateRole.CHAIR
        if "secretaris" in normalised:
            return MandateRole.SECRETARY
        return MandateRole.MEMBER

    @staticmethod
    def _coerce_date(value: datetime | date | None) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        return value

    @staticmethod
    async def _load_existing_parties(
        session: AsyncSession,
        parties: list[Fractie],
    ) -> dict[str, PartyRow]:
        names = {
            party.name
            for party in (TweedeKamerConnector._build_party(fractie) for fractie in parties)
            if party is not None
        }
        if not names:
            return {}

        rows = (await session.execute(select(PartyRow).where(PartyRow.name.in_(names)))).scalars().all()
        return {row.name: row for row in rows}

    @staticmethod
    async def _load_existing_politicians(
        session: AsyncSession,
        people: list[Persoon],
    ) -> dict[str, list[PoliticianRow]]:
        full_names = {
            politician.full_name
            for politician in (TweedeKamerConnector._build_politician(person) for person in people)
            if politician is not None
        }
        if not full_names:
            return {}

        rows = (
            (
                await session.execute(
                    select(PoliticianRow).where(PoliticianRow.full_name.in_(full_names)),
                )
            )
            .scalars()
            .all()
        )
        politicians_by_name: dict[str, list[PoliticianRow]] = {}
        for row in rows:
            politicians_by_name.setdefault(row.full_name, []).append(row)
        return politicians_by_name

    @staticmethod
    async def _load_existing_mandates(
        session: AsyncSession,
        *,
        party_rows_by_id: dict[uuid.UUID, PartyRow],
        politician_rows_by_id: dict[uuid.UUID, PoliticianRow],
        institution_id: uuid.UUID,
        governing_body_id: uuid.UUID,
    ) -> dict[
        tuple[uuid.UUID, uuid.UUID | None, uuid.UUID | None, uuid.UUID | None, str, date | None, date | None],
        MandateRow,
    ]:
        politician_rows = list(politician_rows_by_id.values())
        if not politician_rows:
            return {}

        rows = (
            (
                await session.execute(
                    select(MandateRow).where(
                        MandateRow.politician_id.in_([row.id for row in politician_rows]),
                        MandateRow.institution_id == institution_id,
                        MandateRow.governing_body_id == governing_body_id,
                        MandateRow.party_id.in_([row.id for row in party_rows_by_id.values()]),
                    ),
                )
            )
            .scalars()
            .all()
        )
        return {
            TweedeKamerConnector._mandate_key(
                politician_id=row.politician_id,
                party_id=row.party_id,
                institution_id=row.institution_id,
                governing_body_id=row.governing_body_id,
                role=row.role,
                start_date=row.start_date,
                end_date=row.end_date,
            ): row
            for row in rows
        }

    @staticmethod
    def _mandate_key(
        *,
        politician_id: uuid.UUID,
        party_id: uuid.UUID | None,
        institution_id: uuid.UUID | None,
        governing_body_id: uuid.UUID | None,
        role: str,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[uuid.UUID, uuid.UUID | None, uuid.UUID | None, uuid.UUID | None, str, date | None, date | None]:
        return (
            politician_id,
            party_id,
            institution_id,
            governing_body_id,
            role,
            start_date,
            end_date,
        )
