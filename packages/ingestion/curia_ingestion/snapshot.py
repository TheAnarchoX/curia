"""Raw snapshot storage for crawl results."""

from __future__ import annotations

import abc
import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from curia_ingestion.interfaces import CrawlResult

logger = logging.getLogger(__name__)


def _url_hash(url: str) -> str:
    """Deterministic hash for a URL, used as storage key."""
    return hashlib.sha256(url.encode()).hexdigest()


class RawSnapshotStore(abc.ABC):
    """Persists raw :class:`CrawlResult` objects."""

    @abc.abstractmethod
    async def store(self, crawl_result: CrawlResult) -> str:
        """Store a crawl result and return its key (url_hash)."""

    @abc.abstractmethod
    async def retrieve(self, url_hash: str) -> CrawlResult | None:
        """Retrieve a crawl result by hash, or *None* if not found."""

    @abc.abstractmethod
    async def exists(self, url_hash: str) -> bool:
        """Check whether a snapshot with the given hash is stored."""


class FileSystemSnapshotStore(RawSnapshotStore):
    """Stores raw snapshots as JSON files in a local directory."""

    def __init__(self, base_dir: str | Path) -> None:
        """Initialize the store with a base directory for snapshot files."""
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, url_hash: str) -> Path:
        # Use first two characters as a sub-directory to avoid huge flat listings.
        sub = url_hash[:2]
        return self._base_dir / sub / f"{url_hash}.json"

    def _serialise(self, result: CrawlResult) -> dict[str, Any]:
        data = result.model_dump(mode="json")
        # raw_content is bytes – encode to hex for JSON safety
        if result.raw_content is not None:
            data["raw_content"] = result.raw_content.hex()
        return data

    def _deserialise(self, data: dict[str, Any]) -> CrawlResult:
        if data.get("raw_content") is not None:
            data["raw_content"] = bytes.fromhex(data["raw_content"])
        return CrawlResult.model_validate(data)

    async def store(self, crawl_result: CrawlResult) -> str:
        """Store a crawl result as a JSON file and return its URL hash key."""
        key = _url_hash(crawl_result.url)
        path = self._path_for(key)
        payload = json.dumps(self._serialise(crawl_result), default=str)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_text, payload)
        logger.debug("Stored snapshot %s -> %s", key, path)
        return key

    async def retrieve(self, url_hash: str) -> CrawlResult | None:
        """Retrieve a crawl result by hash, or None if not found."""
        path = self._path_for(url_hash)
        if not await asyncio.to_thread(path.exists):
            return None
        data = json.loads(await asyncio.to_thread(path.read_text))
        return self._deserialise(data)

    async def exists(self, url_hash: str) -> bool:
        """Check whether a snapshot with the given hash is stored."""
        return await asyncio.to_thread(self._path_for(url_hash).exists)
