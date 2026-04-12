"""Mapper from iBabs source models to canonical assertion data and ORM persistence."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime

from curia_domain.db.models import (
    DecisionRow,
    DocumentRow,
    MeetingRow,
    MotionRow,
    PartyRow,
    PoliticianRow,
    VoteRow,
)
from curia_domain.enums import (
    DecisionType,
    DocumentType,
    MeetingStatus,
    PropositionStatus,
)
from curia_ingestion.interfaces import ParsedEntity, ParseResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from curia_connectors_ibabs.models.pages import (
    IbabsAgendaItem,
    IbabsDocumentLink,
    IbabsMeetingDetail,
    IbabsMeetingSummary,
    IbabsMemberRosterEntry,
    IbabsPartyRosterEntry,
    IbabsReportEntry,
    IbabsSpeakerEvent,
)

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class EntityMapResult:
    """Outcome of mapping and persisting a batch of parsed entities."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Entity mapper — ParseResult → ORM rows
# ---------------------------------------------------------------------------


class IbabsEntityMapper:
    """Convert parsed iBabs entities into SQLAlchemy ORM rows and persist them.

    Each entity type has an ``_upsert_*`` handler that looks up an existing
    row by a natural key (e.g. party name, meeting source URL) and either
    creates a new row or updates the existing one.  This ensures re-crawling
    the same pages does not produce duplicate records.
    """

    def __init__(
        self,
        session: AsyncSession,
        governing_body_id: uuid.UUID,
    ) -> None:
        """Initialise the mapper with an async session and governing body context."""
        self._session = session
        self._governing_body_id = governing_body_id
        self._handlers: dict[str, Callable[[ParsedEntity], Awaitable[bool]]] = {
            "party_roster": self._upsert_party,
            "member_roster": self._upsert_politician,
            "meeting_summary": self._upsert_meeting,
            "meeting_detail": self._upsert_meeting,
            "report": self._upsert_document,
            "document_link": self._upsert_document,
            "motion": self._upsert_motion,
            "vote": self._upsert_vote,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def map_and_persist(self, parse_result: ParseResult) -> EntityMapResult:
        """Map every entity in *parse_result* to ORM rows and persist them."""
        result = EntityMapResult()

        for entity in parse_result.entities:
            handler = self._handlers.get(entity.entity_type)
            if handler is None:
                result.skipped += 1
                continue

            try:
                created = await handler(entity)
                if created:
                    result.created += 1
                else:
                    result.updated += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"Error mapping {entity.entity_type} ({entity.external_id}): {exc}")

        await self._session.flush()
        return result

    # ------------------------------------------------------------------
    # Party
    # ------------------------------------------------------------------

    async def _upsert_party(self, entity: ParsedEntity) -> bool:
        data = entity.data
        name: str = data.get("party_name", "")

        stmt = select(PartyRow).where(PartyRow.name == name)
        row = (await self._session.execute(stmt)).scalar_one_or_none()

        if row is None:
            row = PartyRow(
                name=name,
                abbreviation=data.get("abbreviation"),
            )
            self._session.add(row)
            return True

        if data.get("abbreviation"):
            row.abbreviation = data["abbreviation"]
        return False

    # ------------------------------------------------------------------
    # Politician
    # ------------------------------------------------------------------

    async def _upsert_politician(self, entity: ParsedEntity) -> bool:
        data = entity.data
        full_name: str = data.get("name", "")

        stmt = select(PoliticianRow).where(PoliticianRow.full_name == full_name)
        row = (await self._session.execute(stmt)).scalar_one_or_none()

        if row is None:
            row = PoliticianRow(
                full_name=full_name,
                notes=data.get("role"),
            )
            self._session.add(row)
            return True

        if data.get("role"):
            row.notes = data["role"]
        return False

    # ------------------------------------------------------------------
    # Meeting
    # ------------------------------------------------------------------

    async def _upsert_meeting(self, entity: ParsedEntity) -> bool:
        data = entity.data
        source_url: str = data.get("url", "")

        stmt = select(MeetingRow).where(MeetingRow.source_url == source_url)
        row = (await self._session.execute(stmt)).scalar_one_or_none()

        scheduled_start = self._parse_datetime(data.get("date"))
        status = data.get("status", MeetingStatus.SCHEDULED)

        if row is None:
            row = MeetingRow(
                governing_body_id=self._governing_body_id,
                title=data.get("title"),
                scheduled_start=scheduled_start,
                location=data.get("location"),
                source_url=source_url,
                status=status,
            )
            self._session.add(row)
            return True

        if data.get("title"):
            row.title = data["title"]
        if scheduled_start:
            row.scheduled_start = scheduled_start
        if data.get("location"):
            row.location = data["location"]
        if data.get("status"):
            row.status = data["status"]
        return False

    # ------------------------------------------------------------------
    # Document (report / document link)
    # ------------------------------------------------------------------

    async def _upsert_document(self, entity: ParsedEntity) -> bool:
        data = entity.data
        source_url: str = data.get("url", "")

        stmt = select(DocumentRow).where(DocumentRow.source_url == source_url)
        row = (await self._session.execute(stmt)).scalar_one_or_none()

        doc_type = DocumentType.REPORT if entity.entity_type == "report" else DocumentType.OTHER

        if row is None:
            row = DocumentRow(
                title=data.get("title"),
                document_type=doc_type,
                source_url=source_url,
                mime_type=data.get("mime_type"),
            )
            self._session.add(row)
            return True

        if data.get("title"):
            row.title = data["title"]
        if data.get("mime_type"):
            row.mime_type = data["mime_type"]
        return False

    # ------------------------------------------------------------------
    # Motion
    # ------------------------------------------------------------------

    async def _upsert_motion(self, entity: ParsedEntity) -> bool:
        data = entity.data
        title: str = data.get("title", "")

        stmt = select(MotionRow).where(MotionRow.title == title)
        row = (await self._session.execute(stmt)).scalar_one_or_none()

        if row is None:
            row = MotionRow(
                title=title,
                body=data.get("body"),
                status=data.get("status", PropositionStatus.SUBMITTED),
            )
            self._session.add(row)
            return True

        if data.get("body"):
            row.body = data["body"]
        if data.get("status"):
            row.status = data["status"]
        return False

    # ------------------------------------------------------------------
    # Vote
    # ------------------------------------------------------------------

    async def _upsert_vote(self, entity: ParsedEntity) -> bool:
        data = entity.data
        meeting_source_url: str = data.get("meeting_source_url", "")

        # Resolve the meeting this vote belongs to.
        meeting_row: MeetingRow | None = None
        if meeting_source_url:
            stmt = select(MeetingRow).where(
                MeetingRow.source_url == meeting_source_url,
            )
            meeting_row = (await self._session.execute(stmt)).scalar_one_or_none()

        if meeting_row is None:
            raise ValueError(
                f"Cannot persist vote without a linked meeting (meeting_source_url={meeting_source_url!r})"
            )

        # Get or create a Decision for this vote.
        stmt_dec = select(DecisionRow).where(
            DecisionRow.meeting_id == meeting_row.id,
            DecisionRow.description == data.get("description", ""),
        )
        decision = (await self._session.execute(stmt_dec)).scalar_one_or_none()

        if decision is None:
            decision = DecisionRow(
                meeting_id=meeting_row.id,
                decision_type=DecisionType.VOTE,
                outcome=data.get("outcome"),
                description=data.get("description", ""),
            )
            self._session.add(decision)
            await self._session.flush()

        # Upsert the vote itself.
        stmt_vote = select(VoteRow).where(
            VoteRow.decision_id == decision.id,
        )
        vote_row = (await self._session.execute(stmt_vote)).scalar_one_or_none()

        if vote_row is None:
            vote_row = VoteRow(
                decision_id=decision.id,
                outcome=data.get("outcome"),
                votes_for=data.get("votes_for"),
                votes_against=data.get("votes_against"),
                votes_abstain=data.get("votes_abstain"),
            )
            self._session.add(vote_row)
            return True

        vote_row.outcome = data.get("outcome")
        vote_row.votes_for = data.get("votes_for")
        vote_row.votes_against = data.get("votes_against")
        vote_row.votes_abstain = data.get("votes_abstain")
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Best-effort ISO-8601 datetime/date parsing."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None


class IbabsCanonicalMapper:
    """Maps iBabs source-specific models to lists of canonical assertion dicts.

    Each ``map_*`` method returns ``list[dict]`` where every dict represents
    one assertion suitable for the Curia domain layer.  The exact assertion
    schema is owned by ``curia-domain``; here we produce the *data* portion
    that will be wrapped in an ``Assertion`` envelope by the ingestion
    orchestrator.
    """

    # ------------------------------------------------------------------
    # Meeting summary (from list pages)
    # ------------------------------------------------------------------

    def map_meeting_summary(self, summary: IbabsMeetingSummary) -> list[dict]:
        """Map a meeting summary to canonical assertion dicts."""
        return [
            {
                "entity_type": "meeting",
                "external_id": summary.meeting_id,
                "attributes": {
                    "title": summary.title,
                    "date": summary.date.isoformat(),
                    "url": summary.url,
                    "status": summary.status,
                },
                "source_system": "ibabs",
            }
        ]

    # ------------------------------------------------------------------
    # Meeting detail
    # ------------------------------------------------------------------

    def map_meeting_detail(self, detail: IbabsMeetingDetail) -> list[dict]:
        """Map a meeting detail with agenda items and documents to assertions."""
        assertions: list[dict] = [
            {
                "entity_type": "meeting",
                "external_id": detail.meeting_id,
                "attributes": {
                    "title": detail.title,
                    "date": detail.date.isoformat(),
                    "location": detail.location,
                    "url": detail.url,
                },
                "source_system": "ibabs",
            }
        ]

        for item in detail.agenda_items:
            assertions.extend(self.map_agenda_item(item, meeting_id=detail.meeting_id))

        for doc in detail.documents:
            assertions.extend(self.map_document_link(doc, parent_id=detail.meeting_id))

        return assertions

    # ------------------------------------------------------------------
    # Agenda item
    # ------------------------------------------------------------------

    def map_agenda_item(
        self,
        item: IbabsAgendaItem,
        meeting_id: str | None = None,
    ) -> list[dict]:
        """Map an agenda item and its sub-items to canonical assertions."""
        ext_id = f"{meeting_id}:agenda:{item.ordering}" if meeting_id else str(item.ordering)

        assertions: list[dict] = [
            {
                "entity_type": "agenda_item",
                "external_id": ext_id,
                "attributes": {
                    "ordering": item.ordering,
                    "title": item.title,
                    "description": item.description,
                },
                "relations": ([{"type": "belongs_to_meeting", "target_id": meeting_id}] if meeting_id else []),
                "source_system": "ibabs",
            }
        ]

        for sub in item.sub_items:
            assertions.extend(self.map_agenda_item(sub, meeting_id=meeting_id))

        for doc in item.document_links:
            assertions.extend(self.map_document_link(doc, parent_id=ext_id))

        for event in item.speaker_events:
            assertions.extend(self.map_speaker_event(event, agenda_item_id=ext_id))

        return assertions

    # ------------------------------------------------------------------
    # Speaker event
    # ------------------------------------------------------------------

    def map_speaker_event(
        self,
        event: IbabsSpeakerEvent,
        agenda_item_id: str | None = None,
    ) -> list[dict]:
        """Map a speaker event to a canonical assertion dict."""
        return [
            {
                "entity_type": "speaker_event",
                "external_id": f"{event.speaker_name}@{event.start_time or 'unknown'}",
                "attributes": {
                    "speaker_name": event.speaker_name,
                    "party_name": event.party_name,
                    "start_time": event.start_time.isoformat() if event.start_time else None,
                    "end_time": event.end_time.isoformat() if event.end_time else None,
                    "duration_seconds": event.duration_seconds,
                    "role": event.role,
                },
                "relations": ([{"type": "spoken_at", "target_id": agenda_item_id}] if agenda_item_id else []),
                "source_system": "ibabs",
            }
        ]

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def map_report(self, report: IbabsReportEntry) -> list[dict]:
        """Map a report entry and its documents to canonical assertions."""
        assertions: list[dict] = [
            {
                "entity_type": "report",
                "external_id": report.url,
                "attributes": {
                    "title": report.title,
                    "date": report.date.isoformat(),
                    "url": report.url,
                    "report_type": report.report_type,
                },
                "source_system": "ibabs",
            }
        ]

        for doc in report.document_links:
            assertions.extend(self.map_document_link(doc, parent_id=report.url))

        return assertions

    # ------------------------------------------------------------------
    # Document link
    # ------------------------------------------------------------------

    def map_document_link(
        self,
        doc: IbabsDocumentLink,
        parent_id: str | None = None,
    ) -> list[dict]:
        """Map a document link to a canonical assertion dict."""
        return [
            {
                "entity_type": "document",
                "external_id": doc.url,
                "attributes": {
                    "title": doc.title,
                    "url": doc.url,
                    "mime_type": doc.mime_type,
                    "file_size": doc.file_size,
                },
                "relations": ([{"type": "attached_to", "target_id": parent_id}] if parent_id else []),
                "source_system": "ibabs",
            }
        ]

    # ------------------------------------------------------------------
    # Party roster
    # ------------------------------------------------------------------

    def map_party_roster(self, entry: IbabsPartyRosterEntry) -> list[dict]:
        """Map a party roster entry to a canonical assertion dict."""
        assertions: list[dict] = [
            {
                "entity_type": "party",
                "external_id": entry.party_name,
                "attributes": {
                    "party_name": entry.party_name,
                    "abbreviation": entry.abbreviation,
                    "members": entry.members,
                },
                "source_system": "ibabs",
            }
        ]
        return assertions

    # ------------------------------------------------------------------
    # Member roster
    # ------------------------------------------------------------------

    def map_member_roster(self, entry: IbabsMemberRosterEntry) -> list[dict]:
        """Map a member roster entry to a canonical assertion dict."""
        return [
            {
                "entity_type": "member",
                "external_id": entry.name,
                "attributes": {
                    "name": entry.name,
                    "party_name": entry.party_name,
                    "role": entry.role,
                    "active_from": entry.active_from.isoformat() if entry.active_from else None,
                    "active_until": entry.active_until.isoformat() if entry.active_until else None,
                    "photo_url": entry.photo_url,
                },
                "relations": ([{"type": "member_of", "target_id": entry.party_name}] if entry.party_name else []),
                "source_system": "ibabs",
            }
        ]
