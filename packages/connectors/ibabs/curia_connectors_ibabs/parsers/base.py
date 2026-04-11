"""Shared base class for all iBabs HTML parsers."""

from __future__ import annotations

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
    def _extract_text(element: Tag | None) -> str:
        """Safely extract and strip visible text from an element."""
        if element is None:
            return ""
        return element.get_text(separator=" ", strip=True)

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
