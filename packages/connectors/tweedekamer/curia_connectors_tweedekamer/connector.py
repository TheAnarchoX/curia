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

from curia_domain.db.models import (
    AmendmentRow,
    BillRow,
    DecisionRow,
    DocumentRow,
    MandateRow,
    MotionRow,
    PartyRow,
    PoliticianRow,
    VoteRecordRow,
    VoteRow,
)
from curia_domain.enums import (
    BillStatus,
    DecisionType,
    DocumentType,
    JurisdictionLevel,
    MandateRole,
    PropositionStatus,
    VoteOutcome,
)
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
    Besluit,
    DocumentActor,
    Fractie,
    FractieZetelPersoon,
    ODataClient,
    Persoon,
    Stemming,
    ZaakActor,
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


@dataclass
class VoteSyncResult:
    """Outcome of syncing Tweede Kamer voting records."""

    fetched_besluiten: int = 0
    fetched_stemmingen: int = 0
    decisions_created: int = 0
    decisions_existing: int = 0
    votes_created: int = 0
    votes_existing: int = 0
    records_created: int = 0
    records_existing: int = 0
    skipped: int = 0


@dataclass
class BillSyncResult:
    """Outcome of syncing Tweede Kamer bills, motions, and amendments."""

    fetched_zaken: int = 0
    fetched_documents: int = 0
    fetched_dossiers: int = 0
    bills_created: int = 0
    bills_existing: int = 0
    motions_created: int = 0
    motions_existing: int = 0
    amendments_created: int = 0
    amendments_existing: int = 0
    documents_created: int = 0
    documents_existing: int = 0
    skipped: int = 0


# Mapping from Dutch Zaak.Soort values to the target entity type.
_ZAAK_SOORT_MAP: dict[str, str] = {
    "wetsvoorstel": "bill",
    "initiatiefwetsvoorstel": "bill",
    "begroting": "bill",
    "motie": "motion",
    "amendement": "amendment",
}

# Mapping from Dutch Zaak status to BillStatus.
_ZAAK_STATUS_MAP: dict[str, BillStatus] = {
    "aangenomen": BillStatus.ADOPTED,
    "verworpen": BillStatus.REJECTED,
    "ingetrokken": BillStatus.WITHDRAWN,
    "in behandeling": BillStatus.COMMITTEE,
    "aangemeld": BillStatus.INTRODUCED,
}


# Mapping from Dutch Stemming.Soort values to normalised English terms.
_STEMMING_SOORT_MAP: dict[str, str] = {
    "voor": "for",
    "tegen": "against",
    "niet deelgenomen": "not_participated",
}


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

    async def sync_votes(
        self,
        session: AsyncSession,
        *,
        meeting_id: uuid.UUID,
        politician_map: dict[uuid.UUID, PoliticianRow],
        party_map: dict[uuid.UUID, PartyRow],
        besluit_ids: list[uuid.UUID] | None = None,
        odata_client: ODataClient | None = None,
    ) -> VoteSyncResult:
        """Fetch Tweede Kamer voting records and persist them.

        Parameters
        ----------
        session:
            An active async database session.
        meeting_id:
            The meeting to attach decisions/votes to.
        politician_map:
            Mapping from OData ``Persoon.Id`` to the corresponding
            :class:`PoliticianRow`.  Typically built during a prior
            :meth:`sync_members_and_parties` call.
        party_map:
            Mapping from OData ``Fractie.Id`` to the corresponding
            :class:`PartyRow`.
        besluit_ids:
            Optional list of OData Besluit UUIDs to scope the sync to.
            When provided, only Besluit and Stemming records matching
            these IDs are fetched via an OData ``$filter``.  When
            *None*, **all** records are fetched (use with caution on
            large datasets).
        odata_client:
            Optional shared OData client.  If *None*, a new client is
            created and closed at the end of the call.
        """
        manages_client = odata_client is None
        client = odata_client or ODataClient()
        result = VoteSyncResult()

        try:
            besluit_filter: str | None = None
            stemming_filter: str | None = None
            if besluit_ids:
                ids_clause = ",".join(str(bid) for bid in besluit_ids)
                besluit_filter = f"Id in ({ids_clause})"
                stemming_filter = f"Besluit_Id in ({ids_clause})"

            besluiten, stemmingen = await asyncio.gather(
                client.list_besluit(filter=besluit_filter),
                client.list_stemming(
                    expand=["StemmingsSoort"],
                    filter=stemming_filter,
                ),
            )

            result.fetched_besluiten = len(besluiten)
            result.fetched_stemmingen = len(stemmingen)

            # Index Besluit records by their OData Id.
            besluiten_by_id: dict[uuid.UUID, Besluit] = {
                b.id: b for b in besluiten if b.id is not None and not b.verwijderd
            }

            # Group Stemming records by Besluit_Id.
            stemmingen_by_besluit: dict[uuid.UUID, list[Stemming]] = {}
            for stemming in stemmingen:
                if stemming.verwijderd or stemming.besluit_id is None:
                    result.skipped += 1
                    continue
                stemmingen_by_besluit.setdefault(stemming.besluit_id, []).append(stemming)

            # Load existing decisions for this meeting to allow idempotent re-runs.
            existing_decisions = await self._load_existing_decisions(session, meeting_id=meeting_id)
            existing_votes = await self._load_existing_votes(session, decision_ids=set(existing_decisions.values()))

            for besluit_id, besluit_stemmingen in stemmingen_by_besluit.items():
                besluit = besluiten_by_id.get(besluit_id)

                # ----- Decision (Besluit) -----
                decision_row: DecisionRow
                if besluit_id in existing_decisions:
                    decision_row_id = existing_decisions[besluit_id]
                    stmt = select(DecisionRow).where(DecisionRow.id == decision_row_id)
                    decision_row = (await session.execute(stmt)).scalar_one()
                    result.decisions_existing += 1
                else:
                    description = besluit.besluit_tekst if besluit else None
                    decision_row = DecisionRow(
                        meeting_id=meeting_id,
                        decision_type=DecisionType.VOTE,
                        description=description,
                        external_id=str(besluit_id),
                    )
                    session.add(decision_row)
                    await session.flush()
                    existing_decisions[besluit_id] = decision_row.id
                    result.decisions_created += 1

                # ----- Vote (aggregate) -----
                vote_row: VoteRow
                if decision_row.id in existing_votes:
                    vote_row = existing_votes[decision_row.id]
                    result.votes_existing += 1
                else:
                    counts = self._aggregate_stemming(besluit_stemmingen)
                    vote_row = VoteRow(
                        decision_id=decision_row.id,
                        proposition_type=besluit.stemmings_soort if besluit else None,
                        outcome=counts["outcome"],
                        votes_for=counts["votes_for"],
                        votes_against=counts["votes_against"],
                        votes_abstain=counts["votes_abstain"],
                    )
                    session.add(vote_row)
                    await session.flush()
                    existing_votes[decision_row.id] = vote_row
                    result.votes_created += 1

                # ----- VoteRecords (per-faction / per-member) -----
                incoming_ids = {str(s.id) for s in besluit_stemmingen if s.id is not None}
                existing_records = await self._load_existing_vote_records(session, incoming_external_ids=incoming_ids)

                for stemming in besluit_stemmingen:
                    if stemming.id is None:
                        result.skipped += 1
                        continue
                    odata_id = str(stemming.id)
                    if odata_id in existing_records:
                        result.records_existing += 1
                        continue

                    value = self._map_stemming_soort(stemming.soort)
                    politician_row = politician_map.get(stemming.persoon_id) if stemming.persoon_id else None
                    party_row = party_map.get(stemming.fractie_id) if stemming.fractie_id else None
                    size = (
                        stemming.fractie_grootte
                        if stemming.fractie_grootte is not None
                        else 1
                        if stemming.persoon_id is not None
                        else 0
                    )

                    record_row = VoteRecordRow(
                        vote_id=vote_row.id,
                        politician_id=politician_row.id if politician_row else None,
                        party_id=party_row.id if party_row else None,
                        value=value,
                        party_size=size,
                        is_mistake=bool(stemming.vergissing),
                        external_id=odata_id,
                    )
                    session.add(record_row)
                    existing_records[odata_id] = record_row
                    result.records_created += 1

            await session.flush()
            return result
        finally:
            if manages_client:
                await client.aclose()

    async def sync_bills_and_motions(
        self,
        session: AsyncSession,
        *,
        governing_body_id: uuid.UUID,
        politician_map: dict[uuid.UUID, PoliticianRow] | None = None,
        odata_client: ODataClient | None = None,
    ) -> BillSyncResult:
        """Fetch Tweede Kamer legislative cases and persist bills, motions, amendments, and documents.

        Parameters
        ----------
        session:
            An active async database session.
        governing_body_id:
            The governing body to associate bills with.
        politician_map:
            Optional mapping from OData ``Persoon.Id`` to the corresponding
            :class:`PoliticianRow`.  Used to resolve proposer IDs on motions
            and amendments.
        odata_client:
            Optional shared OData client.  If *None*, a new client is
            created and closed at the end of the call.
        """
        manages_client = odata_client is None
        client = odata_client or ODataClient()
        result = BillSyncResult()
        politician_map = politician_map or {}

        try:
            zaken, zaak_actors, documents, doc_actors, dossiers = await asyncio.gather(
                client.list_zaak(),
                client.list_zaakactor(),
                client.list_document(),
                client.list_documentactor(),
                client.list_kamerstukdossier(),
            )

            result.fetched_zaken = len(zaken)
            result.fetched_documents = len(documents)
            result.fetched_dossiers = len(dossiers)

            # Build lookup indexes
            actors_by_zaak: dict[uuid.UUID, list[ZaakActor]] = {}
            for actor in zaak_actors:
                if actor.zaak_id is not None and not actor.verwijderd:
                    actors_by_zaak.setdefault(actor.zaak_id, []).append(actor)

            doc_actors_by_doc: dict[uuid.UUID, list[DocumentActor]] = {}
            for da in doc_actors:
                if da.document_id is not None and not da.verwijderd:
                    doc_actors_by_doc.setdefault(da.document_id, []).append(da)

            # Load existing rows for idempotent upserts
            existing_bills = await self._load_existing_bills(session)
            existing_motions = await self._load_existing_motions(session)
            existing_amendments = await self._load_existing_amendments(session)
            existing_documents = await self._load_existing_documents(session)

            # ----- Process Zaak records -----
            for zaak in zaken:
                if zaak.verwijderd or zaak.id is None:
                    result.skipped += 1
                    continue

                soort = (zaak.soort or "").strip().lower()
                entity_type = _ZAAK_SOORT_MAP.get(soort)

                if entity_type is None:
                    # Not a bill/motion/amendment — skip
                    result.skipped += 1
                    continue

                external_id = str(zaak.id)
                title = zaak.titel or zaak.onderwerp or zaak.citeertitel or f"Zaak {zaak.nummer or external_id}"
                introduced = self._coerce_date(zaak.gestart_op)
                proposer_ids = self._resolve_proposer_ids(
                    actors_by_zaak.get(zaak.id, []),
                    politician_map=politician_map,
                )

                if entity_type == "bill":
                    if external_id in existing_bills:
                        result.bills_existing += 1
                        continue

                    bill_status = self._map_zaak_status(zaak.status)
                    bill_row = BillRow(
                        external_id=external_id,
                        title=title[:512],
                        summary=zaak.onderwerp,
                        bill_type=zaak.soort,
                        status=bill_status,
                        introduced_date=introduced,
                        governing_body_id=governing_body_id,
                        proposer_ids=proposer_ids or None,
                    )
                    session.add(bill_row)
                    existing_bills[external_id] = bill_row
                    result.bills_created += 1

                elif entity_type == "motion":
                    motion_title = title[:512]
                    if motion_title in existing_motions:
                        result.motions_existing += 1
                        continue

                    motion_row = MotionRow(
                        title=motion_title,
                        body=zaak.onderwerp,
                        proposer_ids=proposer_ids or None,
                        status=self._map_zaak_proposition_status(zaak.status),
                    )
                    session.add(motion_row)
                    existing_motions[motion_title] = motion_row
                    result.motions_created += 1

                elif entity_type == "amendment":
                    amendment_title = title[:512]
                    if amendment_title in existing_amendments:
                        result.amendments_existing += 1
                        continue

                    amendment_row = AmendmentRow(
                        title=amendment_title,
                        body=zaak.onderwerp,
                        proposer_ids=proposer_ids or None,
                        status=self._map_zaak_proposition_status(zaak.status),
                    )
                    session.add(amendment_row)
                    existing_amendments[amendment_title] = amendment_row
                    result.amendments_created += 1

            # ----- Process Document records -----
            for doc in documents:
                if doc.verwijderd or doc.id is None:
                    result.skipped += 1
                    continue

                doc_external_id = str(doc.id)
                source_url = f"{_BASE_URL}/Document({doc_external_id})"

                if source_url in existing_documents:
                    result.documents_existing += 1
                    continue

                doc_type = self._map_document_soort(doc.soort)
                doc_title = doc.titel or doc.onderwerp or doc.citeertitel or f"Document {doc.document_nummer or ''}"

                doc_row = DocumentRow(
                    title=doc_title[:512] if doc_title else None,
                    document_type=doc_type,
                    source_url=source_url,
                    mime_type=doc.content_type,
                )
                session.add(doc_row)
                existing_documents[source_url] = doc_row
                result.documents_created += 1

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

    # ------------------------------------------------------------------
    # Vote-sync helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_stemming_soort(soort: str | None) -> str:
        """Convert a Dutch Stemming.Soort value to an English label."""
        if soort is None:
            return "unknown"
        return _STEMMING_SOORT_MAP.get(soort.strip().lower(), "unknown")

    @staticmethod
    def _aggregate_stemming(stemmingen: list[Stemming]) -> dict[str, Any]:
        """Compute aggregate vote counts from a list of Stemming records."""
        votes_for = 0
        votes_against = 0
        votes_abstain = 0
        for stemming in stemmingen:
            # FractieGrootte is the number of faction members voting this way.
            # When it is None and a Persoon_Id is set, the record represents a
            # single member's individual vote so we default to 1.  Otherwise we
            # default to 0 to avoid inflating totals.
            if stemming.fractie_grootte is not None:
                size = stemming.fractie_grootte
            elif stemming.persoon_id is not None:
                size = 1
            else:
                size = 0
            mapped = TweedeKamerConnector._map_stemming_soort(stemming.soort)
            if mapped == "for":
                votes_for += size
            elif mapped == "against":
                votes_against += size
            elif mapped == "not_participated":
                votes_abstain += size

        outcome: str | None = None
        if votes_for > votes_against:
            outcome = VoteOutcome.ADOPTED
        elif votes_against > votes_for:
            outcome = VoteOutcome.REJECTED
        elif votes_for == votes_against and (votes_for + votes_against) > 0:
            outcome = VoteOutcome.TIED

        return {
            "votes_for": votes_for,
            "votes_against": votes_against,
            "votes_abstain": votes_abstain,
            "outcome": outcome,
        }

    @staticmethod
    async def _load_existing_decisions(
        session: AsyncSession,
        *,
        meeting_id: uuid.UUID,
    ) -> dict[uuid.UUID, uuid.UUID]:
        """Load existing decisions for a meeting keyed by OData Besluit UUID.

        Returns a mapping ``{besluit_odata_uuid: decision_row_id}``
        for decisions that have an ``external_id`` set.
        """
        rows = (
            (
                await session.execute(
                    select(DecisionRow).where(
                        DecisionRow.meeting_id == meeting_id,
                        DecisionRow.external_id.isnot(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        mapping: dict[uuid.UUID, uuid.UUID] = {}
        for row in rows:
            if row.external_id is not None:
                try:
                    mapping[uuid.UUID(row.external_id)] = row.id
                except ValueError:
                    pass
        return mapping

    @staticmethod
    async def _load_existing_votes(
        session: AsyncSession,
        *,
        decision_ids: set[uuid.UUID],
    ) -> dict[uuid.UUID, VoteRow]:
        """Load existing VoteRow objects keyed by decision_id."""
        if not decision_ids:
            return {}
        rows = (await session.execute(select(VoteRow).where(VoteRow.decision_id.in_(decision_ids)))).scalars().all()
        return {row.decision_id: row for row in rows}

    @staticmethod
    async def _load_existing_vote_records(
        session: AsyncSession,
        *,
        incoming_external_ids: set[str],
    ) -> dict[str, VoteRecordRow]:
        """Load existing VoteRecordRow objects keyed by external_id.

        ``VoteRecordRow.external_id`` is globally unique, so we look up by
        the set of incoming external IDs rather than scoping to a single
        vote to detect records that may have been synced under a different
        vote.
        """
        if not incoming_external_ids:
            return {}
        rows = (
            (await session.execute(select(VoteRecordRow).where(VoteRecordRow.external_id.in_(incoming_external_ids))))
            .scalars()
            .all()
        )
        return {row.external_id: row for row in rows if row.external_id is not None}

    # ------------------------------------------------------------------
    # Bill-sync helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_zaak_status(status: str | None) -> str:
        """Convert a Dutch Zaak.Status value to a :class:`BillStatus` value."""
        if status is None:
            return BillStatus.OTHER
        return _ZAAK_STATUS_MAP.get(status.strip().lower(), BillStatus.OTHER)

    @staticmethod
    def _map_zaak_proposition_status(status: str | None) -> str:
        """Convert a Dutch Zaak.Status value to a :class:`PropositionStatus` value."""
        if status is None:
            return PropositionStatus.OTHER
        mapping: dict[str, str] = {
            "aangenomen": PropositionStatus.ADOPTED,
            "verworpen": PropositionStatus.REJECTED,
            "ingetrokken": PropositionStatus.WITHDRAWN,
            "in behandeling": PropositionStatus.DEBATED,
            "aangemeld": PropositionStatus.SUBMITTED,
        }
        return mapping.get(status.strip().lower(), PropositionStatus.OTHER)

    @staticmethod
    def _map_document_soort(soort: str | None) -> str:
        """Convert a Dutch Document.Soort value to a :class:`DocumentType` value."""
        if soort is None:
            return DocumentType.OTHER
        mapping: dict[str, str] = {
            "wetsvoorstel": DocumentType.BILL,
            "motie": DocumentType.MOTION,
            "amendement": DocumentType.AMENDMENT,
            "verslag": DocumentType.REPORT,
            "brief": DocumentType.OTHER,
            "nota": DocumentType.POLICY_DOCUMENT,
        }
        return mapping.get(soort.strip().lower(), DocumentType.OTHER)

    @staticmethod
    def _resolve_proposer_ids(
        actors: list[ZaakActor],
        *,
        politician_map: dict[uuid.UUID, PoliticianRow],
    ) -> list[uuid.UUID]:
        """Resolve ZaakActor proposers to Curia politician row IDs."""
        ids: list[uuid.UUID] = []
        for actor in actors:
            if actor.relatie and actor.relatie.lower() in ("indiener", "medeindiener"):
                if actor.persoon_id is not None:
                    pol = politician_map.get(actor.persoon_id)
                    if pol is not None:
                        ids.append(pol.id)
        return ids

    @staticmethod
    async def _load_existing_bills(session: AsyncSession) -> dict[str, BillRow]:
        """Load existing BillRow objects keyed by external_id."""
        rows = (await session.execute(select(BillRow).where(BillRow.external_id.isnot(None)))).scalars().all()
        return {row.external_id: row for row in rows if row.external_id is not None}

    @staticmethod
    async def _load_existing_motions(session: AsyncSession) -> dict[str, MotionRow]:
        """Load existing MotionRow objects keyed by title (used for dedup)."""
        rows = (await session.execute(select(MotionRow))).scalars().all()
        return {row.title: row for row in rows}

    @staticmethod
    async def _load_existing_amendments(session: AsyncSession) -> dict[str, AmendmentRow]:
        """Load existing AmendmentRow objects keyed by title (used for dedup)."""
        rows = (await session.execute(select(AmendmentRow))).scalars().all()
        return {row.title: row for row in rows}

    @staticmethod
    async def _load_existing_documents(session: AsyncSession) -> dict[str, DocumentRow]:
        """Load existing DocumentRow objects keyed by source_url."""
        rows = (await session.execute(select(DocumentRow).where(DocumentRow.source_url.isnot(None)))).scalars().all()
        return {row.source_url: row for row in rows if row.source_url is not None}
