"""Core ingestion interfaces."""
from __future__ import annotations
import abc
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
import uuid

class SourceConnectorMeta(BaseModel):
    """Metadata about a source connector."""
    source_type: str
    name: str
    version: str
    description: str
    capabilities: list[str] = Field(default_factory=list)

class CrawlConfig(BaseModel):
    """Configuration for a crawl job."""
    source_id: uuid.UUID
    base_url: str
    max_pages: int = 1000
    rate_limit_rps: float = 2.0
    timeout_seconds: float = 30.0
    retry_max: int = 3
    checkpoint: dict[str, Any] = Field(default_factory=dict)

class CrawlResult(BaseModel):
    """Result of a single page crawl."""
    url: str
    status_code: int
    content_hash: str
    fetched_at: datetime
    content_type: str
    raw_content: bytes | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    discovered_urls: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

class SourceConnector(abc.ABC):
    """Base class for all source connectors."""
    
    @abc.abstractmethod
    def get_meta(self) -> SourceConnectorMeta: ...
    
    @abc.abstractmethod
    async def discover_pages(self, config: CrawlConfig) -> list[str]: ...
    
    @abc.abstractmethod
    async def crawl_page(self, url: str, config: CrawlConfig) -> CrawlResult: ...
    
    @abc.abstractmethod
    async def get_checkpoint(self) -> dict[str, Any]: ...
    
    @abc.abstractmethod
    async def set_checkpoint(self, checkpoint: dict[str, Any]) -> None: ...

class ParsedEntity(BaseModel):
    """A single entity extracted by a parser."""
    entity_type: str
    source_url: str
    external_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    evidence_snippet: str | None = None

class ParseResult(BaseModel):
    """Result of parsing a crawled page."""
    source_url: str
    parser_name: str
    parser_version: str
    parsed_at: datetime
    entities: list[ParsedEntity] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    confidence: float = 1.0

class Parser(abc.ABC):
    """Base class for source-specific parsers."""
    
    @abc.abstractmethod
    def can_parse(self, url: str, content_type: str) -> bool: ...
    
    @abc.abstractmethod
    def parse(self, crawl_result: CrawlResult) -> ParseResult: ...
