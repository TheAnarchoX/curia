"""Worker task tests for the iBabs Celery sync pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from celery import Signature
from curia_ingestion.interfaces import CrawlResult, ParsedEntity, ParseResult

from apps.worker.app.tasks.crawl import crawl_page, map_page, parse_page, persist_page
from apps.worker.app.tasks.source_sync import build_ibabs_sync_signatures, sync_source


def _sync_state() -> dict[str, Any]:
    return {
        "source_id": "ibabs-source",
        "source_type": "ibabs",
        "connector": {
            "base_url": "https://almelo.bestuurlijkeinformatie.nl",
            "municipality_slug": "almelo",
        },
        "crawl_config": {
            "source_id": "f1c6546e-819f-56e9-8d6b-c6bdc0754154",
            "base_url": "https://almelo.bestuurlijkeinformatie.nl",
            "max_pages": 100,
            "rate_limit_rps": 2.0,
            "timeout_seconds": 30.0,
            "retry_max": 3,
            "checkpoint": {},
        },
        "governing_body_id": "8d67cac7-d6c0-4fa4-bfbd-fe93aaea48a4",
        "checkpoint": {},
        "sync_errors": [],
    }


def _crawl_result(url: str) -> CrawlResult:
    return CrawlResult(
        url=url,
        status_code=200,
        content_hash="hash",
        fetched_at=datetime.now(UTC),
        content_type="text/html",
        raw_content=b"<html></html>",
    )


def _parse_result(url: str, entity_type: str = "meeting_summary") -> ParseResult:
    return ParseResult(
        source_url=url,
        parser_name="stub-parser",
        parser_version="0.1.0",
        parsed_at=datetime.now(UTC),
        entities=[
            ParsedEntity(
                entity_type=entity_type,
                source_url=url,
                external_id="entity-1",
                data={
                    "title": "Raadsvergadering",
                    "date": "2026-04-01",
                    "url": url,
                    "status": "scheduled",
                },
            )
        ],
    )


def test_sync_source_uses_configured_municipality_and_builds_expected_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sync_source should schedule crawl → parse → map → persist for each page."""
    monkeypatch.setenv("IBABS_BASE_URL", "https://heerenveen.bestuurlijkeinformatie.nl")
    monkeypatch.setenv("IBABS_MUNICIPALITY_SLUG", "heerenveen")
    monkeypatch.setenv("IBABS_GOVERNING_BODY_ID", "9cb7d7c2-d58e-49d6-af80-b06186f89a75")

    pages = [
        "https://heerenveen.bestuurlijkeinformatie.nl/meetings",
        "https://heerenveen.bestuurlijkeinformatie.nl/reports",
    ]

    async def fake_discover(sync_state: dict[str, Any]) -> list[str]:
        assert sync_state["connector"]["municipality_slug"] == "heerenveen"
        return pages

    captured: dict[str, Any] = {}

    def fake_chain(*signatures: Signature) -> Any:
        captured["task_names"] = [signature.task for signature in signatures]

        class _FakeChain:
            def apply_async(self) -> SimpleNamespace:
                return SimpleNamespace(id="job-123")

        return _FakeChain()

    monkeypatch.setattr("apps.worker.app.tasks.source_sync._discover_ibabs_pages", fake_discover)
    monkeypatch.setattr("apps.worker.app.tasks.source_sync.chain", fake_chain)

    result = sync_source.run("ibabs")

    assert result == {
        "status": "started",
        "message": "Started iBabs sync for source ibabs",
        "source_id": "ibabs",
        "municipality": "heerenveen",
        "pages": 2,
        "task_id": "job-123",
    }
    assert captured["task_names"] == [
        "crawl.crawl_page",
        "crawl.parse_page",
        "crawl.map_page",
        "crawl.persist_page",
        "crawl.crawl_page",
        "crawl.parse_page",
        "crawl.map_page",
        "crawl.persist_page",
    ]


def test_build_ibabs_sync_signatures_repeats_full_page_pipeline() -> None:
    """Each discovered page should expand to the full crawl/parse/map/persist chain."""
    signatures = build_ibabs_sync_signatures(
        _sync_state(),
        [
            "https://almelo.bestuurlijkeinformatie.nl/meetings",
            "https://almelo.bestuurlijkeinformatie.nl/reports",
        ],
    )

    assert [signature.task for signature in signatures] == [
        "crawl.crawl_page",
        "crawl.parse_page",
        "crawl.map_page",
        "crawl.persist_page",
        "crawl.crawl_page",
        "crawl.parse_page",
        "crawl.map_page",
        "crawl.persist_page",
    ]


def test_pipeline_updates_checkpoint_after_successful_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """persist_page should advance the checkpoint when a page succeeds."""

    async def fake_crawl(sync_state: dict[str, Any], url: str) -> CrawlResult:
        return _crawl_result(url)

    def fake_parse(crawl_result: CrawlResult) -> ParseResult:
        return _parse_result(crawl_result.url)

    async def fake_persist(
        sync_state: dict[str, Any],
        parse_payload: dict[str, Any],
        mapped_entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        assert mapped_entities[0]["entity_type"] == "meeting_summary"
        return {"created": 1, "updated": 0, "skipped": 0, "errors": []}

    monkeypatch.setattr("apps.worker.app.tasks.crawl._crawl_page_async", fake_crawl)
    monkeypatch.setattr("apps.worker.app.tasks.crawl._parse_crawl_result", fake_parse)
    monkeypatch.setattr("apps.worker.app.tasks.crawl._persist_mapped_page_async", fake_persist)

    url = "https://almelo.bestuurlijkeinformatie.nl/meetings"
    state = crawl_page.run(_sync_state(), url)
    state = parse_page.run(state)
    state = map_page.run(state)
    state = persist_page.run(state)

    assert state["page_error"] is None
    assert state["persist_result"] == {"created": 1, "updated": 0, "skipped": 0, "errors": []}
    assert state["checkpoint"]["last_successful_page_url"] == url
    assert state["checkpoint"]["processed_urls"] == [url]


def test_pipeline_logs_page_errors_without_blocking_later_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed page should not prevent the next page in the chain from succeeding."""
    attempts: list[str] = []

    async def fake_crawl(sync_state: dict[str, Any], url: str) -> CrawlResult:
        attempts.append(url)
        if url.endswith("/broken"):
            raise RuntimeError("boom")
        return _crawl_result(url)

    def fake_parse(crawl_result: CrawlResult) -> ParseResult:
        return _parse_result(crawl_result.url)

    async def fake_persist(
        sync_state: dict[str, Any],
        parse_payload: dict[str, Any],
        mapped_entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {"created": 1, "updated": 0, "skipped": 0, "errors": []}

    monkeypatch.setattr("apps.worker.app.tasks.crawl._crawl_page_async", fake_crawl)
    monkeypatch.setattr("apps.worker.app.tasks.crawl._parse_crawl_result", fake_parse)
    monkeypatch.setattr("apps.worker.app.tasks.crawl._persist_mapped_page_async", fake_persist)

    failed_state = crawl_page.run(_sync_state(), "https://almelo.bestuurlijkeinformatie.nl/broken")
    failed_state = parse_page.run(failed_state)
    failed_state = map_page.run(failed_state)
    failed_state = persist_page.run(failed_state)

    assert "crawl failed" in failed_state["page_error"]
    assert failed_state["checkpoint"] == {}
    assert failed_state["sync_errors"]

    recovered_state = crawl_page.run(failed_state, "https://almelo.bestuurlijkeinformatie.nl/meetings")
    recovered_state = parse_page.run(recovered_state)
    recovered_state = map_page.run(recovered_state)
    recovered_state = persist_page.run(recovered_state)

    assert attempts == [
        "https://almelo.bestuurlijkeinformatie.nl/broken",
        "https://almelo.bestuurlijkeinformatie.nl/meetings",
    ]
    assert recovered_state["page_error"] is None
    assert recovered_state["checkpoint"]["last_successful_page_url"] == (
        "https://almelo.bestuurlijkeinformatie.nl/meetings"
    )
