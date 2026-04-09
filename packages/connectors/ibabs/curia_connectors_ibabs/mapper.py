"""Mapper from iBabs source models to canonical assertion data."""

from __future__ import annotations

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
                "relations": (
                    [{"type": "belongs_to_meeting", "target_id": meeting_id}]
                    if meeting_id
                    else []
                ),
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
                "relations": (
                    [{"type": "spoken_at", "target_id": agenda_item_id}]
                    if agenda_item_id
                    else []
                ),
                "source_system": "ibabs",
            }
        ]

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def map_report(self, report: IbabsReportEntry) -> list[dict]:
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
                "relations": (
                    [{"type": "attached_to", "target_id": parent_id}]
                    if parent_id
                    else []
                ),
                "source_system": "ibabs",
            }
        ]

    # ------------------------------------------------------------------
    # Party roster
    # ------------------------------------------------------------------

    def map_party_roster(self, entry: IbabsPartyRosterEntry) -> list[dict]:
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
                "relations": (
                    [{"type": "member_of", "target_id": entry.party_name}]
                    if entry.party_name
                    else []
                ),
                "source_system": "ibabs",
            }
        ]
