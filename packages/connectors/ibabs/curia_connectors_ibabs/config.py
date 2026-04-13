"""Configuration for the iBabs source connector."""

from __future__ import annotations

from pydantic import BaseModel, Field

INCREMENTAL_SYNC_SECTIONS = ("meetings", "reports")


class IbabsSourceConfig(BaseModel):
    """Configuration specific to an iBabs portal instance."""

    base_url: str = Field(
        description="Root URL of the iBabs portal, e.g. https://ibabs.eu/municipality",
    )
    municipality_slug: str = Field(
        description="URL-safe slug identifying the municipality within iBabs",
    )
    portal_variant: str = Field(
        default="standard",
        description="Portal UI variant — affects HTML structure and available pages",
    )
    known_capabilities: list[str] = Field(
        default_factory=lambda: [
            "meetings",
            "agenda_items",
            "documents",
            "speakers",
            "reports",
            "parties",
            "members",
        ],
        description="List of content types this portal is known to expose",
    )
    custom_paths: dict[str, str] = Field(
        default_factory=lambda: {
            "meetings": "/meetings",
            "reports": "/reports",
            "parties": "/parties",
            "members": "/members",
        },
        description="Override default URL path segments for each content section",
    )
