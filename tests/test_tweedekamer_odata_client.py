"""Unit tests for the Tweede Kamer OData client."""

from __future__ import annotations

import httpx
import pytest
from curia_connectors_tweedekamer.odata_client import (
    CommissieZetel,
    Fractie,
    ODataClient,
    Persoon,
)

TEST_BASE_URL = "https://example.test/OData/v4/2.0/"


async def test_fetch_entities_supports_query_options_and_typed_models() -> None:
    """The client should send supported OData query options and parse typed entities."""
    expected_filter = "Verwijderd eq false"
    expected_select = "Id,Achternaam"
    expected_expand = "Fractie"
    expected_orderby = "Achternaam asc"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/OData/v4/2.0/Persoon"
        assert request.url.params["$filter"] == expected_filter
        assert request.url.params["$select"] == expected_select
        assert request.url.params["$expand"] == expected_expand
        assert request.url.params["$orderby"] == expected_orderby
        assert request.url.params["$top"] == "5"
        assert request.url.params["$skip"] == "10"
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": "fab499e2-93b6-4bba-8266-00014175f6a6",
                        "Achternaam": "Jansen",
                        "Verwijderd": False,
                    }
                ]
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        people = await client.list_persoon(
            filter=expected_filter,
            select=["Id", "Achternaam"],
            expand=["Fractie"],
            orderby=["Achternaam asc"],
            top=5,
            skip=10,
        )

    assert len(people) == 1
    assert isinstance(people[0], Persoon)
    assert str(people[0].id) == "fab499e2-93b6-4bba-8266-00014175f6a6"
    assert people[0].achternaam == "Jansen"
    assert people[0].verwijderd is False


async def test_fetch_entities_follows_odata_next_link_automatically() -> None:
    """The client should follow @odata.nextLink until all pages are collected."""
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.params.get("$skip") == "1":
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "Id": "a9e0f6c1-795e-466b-a85a-a2d017f67a0c",
                            "Achternaam": "De Boer",
                        }
                    ]
                },
                request=request,
            )

        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": "fab499e2-93b6-4bba-8266-00014175f6a6",
                        "Achternaam": "Jansen",
                    }
                ],
                "@odata.nextLink": f"{TEST_BASE_URL}Persoon?$skip=1&$top=1",
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        people = await client.list_persoon(top=1)

    assert len(people) == 2
    assert all(isinstance(person, Persoon) for person in people)
    assert [person.achternaam for person in people] == ["Jansen", "De Boer"]
    assert len(requests) == 2


async def test_fetch_entities_uses_default_model_mapping() -> None:
    """Known entity sets should resolve to their typed model automatically."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/OData/v4/2.0/Fractie"
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": "fab499e2-93b6-4bba-8266-00014175f6a6",
                        "Afkorting": "PvdA",
                        "NaamNL": "Partij van de Arbeid",
                        "AantalZetels": 9,
                    }
                ]
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        fracties: list[Fractie] = await client.fetch_entities("Fractie")

    assert len(fracties) == 1
    assert isinstance(fracties[0], Fractie)
    assert fracties[0].afkorting == "PvdA"
    assert fracties[0].naam_nl == "Partij van de Arbeid"
    assert fracties[0].aantal_zetels == 9


async def test_list_commissielid_uses_commissiezetel_entity_set() -> None:
    """The compatibility helper should fetch the real CommissieZetel entity set."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/OData/v4/2.0/CommissieZetel"
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "Id": "c6a5b3f3-15a1-4dbd-bc69-000131264c8b",
                        "Gewicht": 10000,
                        "Commissie_Id": "fab499e2-93b6-4bba-8266-00014175f6a6",
                    }
                ]
            },
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http_client:
        client = ODataClient(base_url=TEST_BASE_URL, http_client=http_client)
        commissiezetels = await client.list_commissielid()

    assert len(commissiezetels) == 1
    assert isinstance(commissiezetels[0], CommissieZetel)
    assert commissiezetels[0].gewicht == 10000


def test_fetch_entities_rejects_negative_top_or_skip() -> None:
    """Negative pagination values should be rejected before the request is sent."""
    with pytest.raises(ValueError, match=r"\$top"):
        ODataClient._build_query_params(
            filter=None,
            select=None,
            expand=None,
            orderby=None,
            top=-1,
            skip=None,
        )

    with pytest.raises(ValueError, match=r"\$skip"):
        ODataClient._build_query_params(
            filter=None,
            select=None,
            expand=None,
            orderby=None,
            top=None,
            skip=-1,
        )
