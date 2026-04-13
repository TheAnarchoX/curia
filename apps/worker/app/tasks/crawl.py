"""Web crawling tasks."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlparse

from curia_connectors_ibabs.config import INCREMENTAL_SYNC_SECTIONS, IbabsSourceConfig
from curia_connectors_ibabs.connector import IbabsConnector
from curia_connectors_ibabs.mapper import IbabsEntityMapper
from curia_connectors_ibabs.parsers import (
    IbabsAgendaItemParser,
    IbabsDocumentLinkParser,
    IbabsMeetingDetailParser,
    IbabsMeetingListParser,
    IbabsMemberRosterParser,
    IbabsPartyRosterParser,
    IbabsReportParser,
    IbabsSpeakerTimelineParser,
)
from curia_domain.db.models import SourceRow
from curia_domain.db.session import async_session_factory
from curia_ingestion.interfaces import CrawlConfig, CrawlResult, Parser, ParseResult
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from apps.worker.app.celery_app import celery_app

logger = logging.getLogger(__name__)

_MAPPABLE_ENTITY_TYPES = frozenset(
    {
        "document_link",
        "meeting_detail",
        "meeting_summary",
        "member_roster",
        "motion",
        "party_roster",
        "report",
        "vote",
    }
)


def _build_connector(sync_state: dict[str, Any]) -> IbabsConnector:
    connector_config = IbabsSourceConfig.model_validate(sync_state["connector"])
    return IbabsConnector(connector_config)


def _build_crawl_config(sync_state: dict[str, Any]) -> CrawlConfig:
    crawl_config = dict(sync_state["crawl_config"])
    crawl_config["checkpoint"] = _checkpoint_dict(sync_state.get("checkpoint"))
    return CrawlConfig.model_validate(crawl_config)


def _reset_page_state(sync_state: dict[str, Any], url: str) -> dict[str, Any]:
    state = dict(sync_state)
    for transient_key in (
        "crawl_result",
        "parse_result",
        "mapped_entities",
        "mapped_summary",
        "persist_result",
    ):
        state.pop(transient_key, None)
    state["current_url"] = url
    state["page_error"] = None
    state["page_warnings"] = []
    return state


def _append_sync_error(sync_state: dict[str, Any], message: str) -> dict[str, Any]:
    errors = list(sync_state.get("sync_errors") or [])
    errors.append(message)
    sync_state["sync_errors"] = errors
    return sync_state


def _set_page_error(sync_state: dict[str, Any], stage: str, message: str) -> dict[str, Any]:
    error_message = f"{stage} failed for {sync_state.get('current_url', '<unknown>')}: {message}"
    sync_state["page_error"] = error_message
    logger.error(error_message)
    return _append_sync_error(sync_state, error_message)


def _page_is_blocked(sync_state: dict[str, Any]) -> bool:
    return bool(sync_state.get("page_error"))


def _serialise_crawl_result(crawl_result: CrawlResult) -> dict[str, Any]:
    payload = crawl_result.model_dump(mode="json")
    if crawl_result.raw_content is not None:
        payload["raw_content"] = crawl_result.raw_content.hex()
    return payload


def _deserialise_crawl_result(payload: dict[str, Any]) -> CrawlResult:
    data = dict(payload)
    raw_content = data.get("raw_content")
    if isinstance(raw_content, str):
        data["raw_content"] = bytes.fromhex(raw_content)
    return CrawlResult.model_validate(data)


def _serialise_parse_result(parse_result: ParseResult) -> dict[str, Any]:
    return parse_result.model_dump(mode="json")


def _deserialise_parse_result(payload: dict[str, Any]) -> ParseResult:
    return ParseResult.model_validate(payload)


def _get_ibabs_parsers() -> tuple[Parser, ...]:
    return (
        IbabsMeetingDetailParser(),
        IbabsMeetingListParser(),
        IbabsReportParser(),
        IbabsPartyRosterParser(),
        IbabsMemberRosterParser(),
        IbabsDocumentLinkParser(),
        IbabsAgendaItemParser(),
        IbabsSpeakerTimelineParser(),
    )


def _parse_crawl_result(crawl_result: CrawlResult) -> ParseResult:
    for parser in _get_ibabs_parsers():
        if parser.can_parse(crawl_result.url, crawl_result.content_type):
            return parser.parse(crawl_result)

    return ParseResult(
        source_url=crawl_result.url,
        parser_name="ibabs-unmatched",
        parser_version="0.1.0",
        parsed_at=datetime.now(UTC),
        errors=[f"No iBabs parser matched {crawl_result.url} ({crawl_result.content_type})"],
    )


def _map_parse_result(parse_result: ParseResult) -> tuple[list[dict[str, Any]], dict[str, int]]:
    mapped_entities = [
        entity.model_dump(mode="json")
        for entity in parse_result.entities
        if entity.entity_type in _MAPPABLE_ENTITY_TYPES
    ]
    skipped_entities = len(parse_result.entities) - len(mapped_entities)
    return mapped_entities, {
        "mapped_entities": len(mapped_entities),
        "skipped_entities": skipped_entities,
    }


def _checkpoint_dict(checkpoint: Any) -> dict[str, Any]:
    if isinstance(checkpoint, Mapping):
        return dict(checkpoint)
    return {}


def _checkpoint_processed_urls(checkpoint: Mapping[str, Any]) -> list[str]:
    processed_urls = checkpoint.get("processed_urls")
    if isinstance(processed_urls, list):
        return [url for url in processed_urls if isinstance(url, str)]
    return []


def _checkpoint_page_offsets(checkpoint: Mapping[str, Any]) -> dict[str, dict[str, int | str]]:
    page_offsets = checkpoint.get("page_offsets")
    if not isinstance(page_offsets, Mapping):
        return {}

    return {
        section: {key: value for key, value in offset_data.items() if isinstance(key, str)}
        for section, offset_data in page_offsets.items()
        if isinstance(section, str) and isinstance(offset_data, Mapping)
    }


def _build_updated_checkpoint(sync_state: Mapping[str, Any]) -> dict[str, Any]:
    checkpoint = _checkpoint_dict(sync_state.get("checkpoint"))
    processed_urls = _checkpoint_processed_urls(checkpoint)
    current_url = sync_state["current_url"]
    if current_url not in processed_urls:
        processed_urls.append(current_url)
    page_offsets = _checkpoint_page_offsets(checkpoint)
    section = _resolve_incremental_section(sync_state, current_url)
    if section is not None:
        page_offsets[section] = _extract_page_offset(current_url)
    updated_at = datetime.now(UTC).isoformat()
    checkpoint.update(
        {
            "last_successful_page_url": current_url,
            "last_synced_at": updated_at,
            "page_offsets": page_offsets,
            "processed_urls": processed_urls,
            "updated_at": updated_at,
        }
    )
    return checkpoint


def _update_checkpoint(sync_state: dict[str, Any]) -> dict[str, Any]:
    sync_state["checkpoint"] = _build_updated_checkpoint(sync_state)
    return sync_state


def _resolve_incremental_section(sync_state: dict[str, Any], url: str) -> str | None:
    connector_config = IbabsSourceConfig.model_validate(sync_state["connector"])
    current_path = urlparse(url).path.rstrip("/") or "/"

    for section in INCREMENTAL_SYNC_SECTIONS:
        path = connector_config.custom_paths.get(section)
        if path is None:
            continue
        section_url = urljoin(connector_config.base_url.rstrip("/") + "/", path.lstrip("/"))
        section_path = urlparse(section_url).path.rstrip("/") or "/"
        if current_path == section_path:
            return section

    return None


def _extract_page_offset(url: str) -> dict[str, int | str]:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))

    for param in ("page", "pagina", "offset", "start"):
        value = query.get(param)
        if value in (None, ""):
            continue
        try:
            offset_value: int | str = int(value)
        except ValueError:
            offset_value = value
        return {"param": param, "value": offset_value}

    return {"param": "page", "value": 0}


async def _crawl_page_async(sync_state: dict[str, Any], url: str) -> CrawlResult:
    connector = _build_connector(sync_state)
    await connector.set_checkpoint(_checkpoint_dict(sync_state.get("checkpoint")))
    return await connector.crawl_page(url, _build_crawl_config(sync_state))


async def _persist_mapped_page_async(
    sync_state: dict[str, Any],
    parse_payload: dict[str, Any],
    mapped_entities: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    parse_result = _deserialise_parse_result(parse_payload)
    parse_result = parse_result.model_copy(update={"entities": mapped_entities})

    async with async_session_factory() as session:
        mapper = IbabsEntityMapper(
            session=session,
            governing_body_id=uuid.UUID(sync_state["governing_body_id"]),
        )
        map_result = await mapper.map_and_persist(parse_result)
        checkpoint: dict[str, Any] | None = None
        if not map_result.errors:
            checkpoint = _build_updated_checkpoint(sync_state)
            source_id_value = sync_state.get("source_id")
            source_id: uuid.UUID | None = None
            if isinstance(source_id_value, uuid.UUID):
                source_id = source_id_value
            elif isinstance(source_id_value, str):
                try:
                    source_id = uuid.UUID(source_id_value)
                except ValueError:
                    source_id = None

            if source_id is not None:
                source_row = await session.scalar(select(SourceRow).where(SourceRow.id == source_id))
                if source_row is not None:
                    source_config = dict(source_row.config or {})
                    source_config["checkpoint"] = checkpoint
                    source_row.config = source_config
        await session.commit()

    return (
        {
            "created": map_result.created,
            "updated": map_result.updated,
            "skipped": map_result.skipped,
            "errors": list(map_result.errors),
        },
        checkpoint,
    )


@celery_app.task(name="crawl.run_crawl_job")
def run_crawl_job(source_id: str, job_config: dict[str, Any]) -> dict[str, Any]:
    """Execute a crawl job for a given source.

    Iterates over configured pages for the source and enqueues
    individual page-crawl tasks.
    """
    logger.info("Running crawl job for source %s with config %s", source_id, job_config)
    pages = list(job_config.get("pages") or [])
    return {
        "status": "ok",
        "message": f"Crawl job started for source {source_id}",
        "pages": pages,
    }


@celery_app.task(name="crawl.crawl_page")
def crawl_page(sync_state: dict[str, Any], url: str | None = None) -> dict[str, Any]:
    """Crawl a single page from a source.

    Downloads the page content, stores it as a source record, and
    computes a content hash for deduplication.
    """
    current_url = url or sync_state.get("current_url")
    if not isinstance(current_url, str) or not current_url:
        return _set_page_error(dict(sync_state), "crawl", "missing page URL")

    state = _reset_page_state(sync_state, current_url)
    logger.info("Crawling page %s for source %s", current_url, state["source_id"])

    try:
        crawl_result = asyncio.run(_crawl_page_async(state, current_url))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled crawl failure for %s", current_url)
        return _set_page_error(state, "crawl", str(exc))

    if crawl_result.errors and crawl_result.raw_content is None:
        return _set_page_error(state, "crawl", "; ".join(crawl_result.errors))

    if crawl_result.errors:
        for error in crawl_result.errors:
            logger.warning("Crawler reported recoverable issue for %s: %s", current_url, error)
            _append_sync_error(state, f"crawl warning for {current_url}: {error}")

    state["crawl_result"] = _serialise_crawl_result(crawl_result)
    return state


@celery_app.task(name="crawl.parse_page")
def parse_page(sync_state: dict[str, Any]) -> dict[str, Any]:
    """Parse a crawled page into structured iBabs entities."""
    state = dict(sync_state)
    if _page_is_blocked(state):
        return state

    crawl_payload = state.get("crawl_result")
    if not isinstance(crawl_payload, dict):
        return _set_page_error(state, "parse", "missing crawl payload")

    crawl_result = _deserialise_crawl_result(crawl_payload)
    if crawl_result.raw_content is None:
        return _set_page_error(state, "parse", "crawl result had no raw content")

    parse_result = _parse_crawl_result(crawl_result)
    for warning in parse_result.warnings:
        logger.warning("Parser warning for %s: %s", crawl_result.url, warning)
    if parse_result.errors:
        return _set_page_error(state, "parse", "; ".join(parse_result.errors))

    state["page_warnings"] = list(parse_result.warnings)
    state["parse_result"] = _serialise_parse_result(parse_result)
    return state


@celery_app.task(name="crawl.map_page")
def map_page(sync_state: dict[str, Any]) -> dict[str, Any]:
    """Map parsed iBabs entities into persistable payloads."""
    state = dict(sync_state)
    if _page_is_blocked(state):
        return state

    parse_payload = state.get("parse_result")
    if not isinstance(parse_payload, dict):
        return _set_page_error(state, "map", "missing parse payload")

    parse_result = _deserialise_parse_result(parse_payload)
    mapped_entities, mapped_summary = _map_parse_result(parse_result)
    state["mapped_entities"] = mapped_entities
    state["mapped_summary"] = mapped_summary
    return state


@celery_app.task(name="crawl.persist_page")
def persist_page(sync_state: dict[str, Any]) -> dict[str, Any]:
    """Persist mapped entities and advance the sync checkpoint."""
    state = dict(sync_state)
    if _page_is_blocked(state):
        return state

    parse_payload = state.get("parse_result")
    mapped_entities = state.get("mapped_entities")
    if not isinstance(parse_payload, dict):
        return _set_page_error(state, "persist", "missing parse payload")
    if not isinstance(mapped_entities, list):
        return _set_page_error(state, "persist", "missing mapped entities")

    try:
        persist_result, checkpoint = asyncio.run(_persist_mapped_page_async(state, parse_payload, mapped_entities))
    except (SQLAlchemyError, ValueError) as exc:
        logger.exception("Unhandled persist failure for %s", state.get("current_url"))
        return _set_page_error(state, "persist", str(exc))

    for error in persist_result["errors"]:
        logger.error("Persist error for %s: %s", state.get("current_url"), error)
        _append_sync_error(state, f"persist error for {state.get('current_url')}: {error}")

    state["persist_result"] = persist_result
    if checkpoint is not None:
        state["checkpoint"] = checkpoint
    return state
