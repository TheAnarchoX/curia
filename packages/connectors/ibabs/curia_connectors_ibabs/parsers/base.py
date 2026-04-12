"""Shared base class for all iBabs HTML parsers."""

from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from curia_ingestion.interfaces import Parser


class IbabsParser(Parser):
    """Abstract base adding convenience helpers used by every iBabs parser."""

    # Subclasses must set these
    PARSER_NAME: str = "ibabs-base"
    PARSER_VERSION: str = "0.1.0"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_soup(html: bytes | str) -> BeautifulSoup:
        """Create a BeautifulSoup tree using the fast lxml backend."""
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def _extract_text(element: Tag | None, *, exclude_selectors: tuple[str, ...] = ()) -> str:
        """Safely extract and strip visible text from an element."""
        if element is None:
            return ""
        if not exclude_selectors:
            return element.get_text(separator=" ", strip=True)

        cleaned_soup = BeautifulSoup(str(element), "lxml")
        cleaned = cleaned_soup.select_one(element.name) or cleaned_soup
        for selector in exclude_selectors:
            for node in cleaned.select(selector):
                node.decompose()

        return cleaned.get_text(separator=" ", strip=True)

    @staticmethod
    def _extract_links(soup: BeautifulSoup | Tag, base_url: str) -> list[dict[str, str]]:
        """Return a list of ``{title, url}`` dicts for every ``<a>`` inside *soup*."""
        results: list[dict[str, str]] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            absolute = urljoin(base_url, href)
            title = anchor.get_text(strip=True) or absolute
            results.append({"title": title, "url": absolute})
        return results

    @staticmethod
    def _try_parse_date(raw: str) -> date | None:
        """Best-effort parsing for common iBabs date formats."""
        if not raw:
            return None

        normalized = " ".join(raw.split())
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(normalized, fmt).date()
            except ValueError:
                continue

        lowered = normalized.lower()
        lowered = re.sub(
            r"^(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+",
            "",
            lowered,
        )
        month_map = {
            "januari": "January",
            "februari": "February",
            "maart": "March",
            "april": "April",
            "mei": "May",
            "juni": "June",
            "juli": "July",
            "augustus": "August",
            "september": "September",
            "oktober": "October",
            "november": "November",
            "december": "December",
        }
        for nl_month, en_month in month_map.items():
            lowered = lowered.replace(nl_month, en_month)

        try:
            return datetime.strptime(lowered.title(), "%d %B %Y").date()
        except ValueError:
            return None
