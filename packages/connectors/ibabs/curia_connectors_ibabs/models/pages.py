"""Pydantic v2 models representing pages and entities scraped from iBabs portals."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class IbabsDocumentLink(BaseModel):
    """A link to a downloadable document attached to a meeting or agenda item."""

    title: str
    url: str
    mime_type: str | None = None
    file_size: int | None = Field(default=None, description="File size in bytes")


class IbabsSpeakerEvent(BaseModel):
    """A single speaking slot within a meeting or agenda item."""

    speaker_name: str
    party_name: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: float | None = None
    role: str | None = Field(
        default=None,
        description="Role during the event, e.g. 'chair', 'questioner'",
    )


class IbabsAgendaItem(BaseModel):
    """An agenda item within a meeting."""

    ordering: int
    title: str
    description: str = ""
    sub_items: list[IbabsAgendaItem] = Field(default_factory=list)
    document_links: list[IbabsDocumentLink] = Field(default_factory=list)
    speaker_events: list[IbabsSpeakerEvent] = Field(default_factory=list)


class IbabsMeetingSummary(BaseModel):
    """Compact representation of a meeting as it appears in list views."""

    title: str
    date: date
    url: str
    meeting_id: str
    status: str = Field(
        default="unknown",
        description="e.g. 'scheduled', 'completed', 'cancelled'",
    )


class IbabsMeetingListPage(BaseModel):
    """A single page of the meetings overview, with optional pagination link."""

    meetings: list[IbabsMeetingSummary] = Field(default_factory=list)
    next_page_url: str | None = None


class IbabsMeetingDetail(BaseModel):
    """Full detail view of a single meeting."""

    title: str
    date: date
    location: str = ""
    url: str
    meeting_id: str
    agenda_items: list[IbabsAgendaItem] = Field(default_factory=list)
    documents: list[IbabsDocumentLink] = Field(default_factory=list)


class IbabsReportEntry(BaseModel):
    """A report (e.g. minutes, decision list) published on the portal."""

    title: str
    date: date
    url: str
    report_type: str = Field(
        default="unknown",
        description="e.g. 'minutes', 'decision_list', 'proceedings'",
    )
    document_links: list[IbabsDocumentLink] = Field(default_factory=list)


class IbabsPartyRosterEntry(BaseModel):
    """A political party and its known members."""

    party_name: str
    abbreviation: str | None = None
    members: list[str] = Field(default_factory=list)


class IbabsMemberRosterEntry(BaseModel):
    """An individual council/committee member."""

    name: str
    party_name: str | None = None
    role: str | None = None
    active_from: date | None = None
    active_until: date | None = None
    photo_url: str | None = None
