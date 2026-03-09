from __future__ import annotations

import pytest
from sanic import response

from tests.conftest import assert_content_type, assert_json_contract


@pytest.mark.endpoint
@pytest.mark.contract
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/source.json",
        "/api/v1/person.json",
        "/api/v1/institution.json",
        "/api/v1/work.json",
        "/api/v1/publication.json",
        "/api/v1/context.json",
    ],
)
def test_api_context_endpoints(client, path: str):
    _, resp = client.get(path)
    assert_json_contract(resp, status=200, required_keys=["@context"])


@pytest.mark.endpoint
@pytest.mark.contract
def test_front_route_returns_html(client, mocker):
    async def fake_front(_req):
        return response.html("<html><body>ok</body></html>")

    mocker.patch("search_server.server.handle_front_request", side_effect=fake_front)

    _, resp = client.get("/")
    assert resp.status == 200
    assert_content_type(resp, "text/html")
    assert "ok" in resp.text


@pytest.mark.endpoint
@pytest.mark.contract
def test_about_route_json_contract(client, mocker):
    class FakeSolrConnection:
        @staticmethod
        async def get(_ident, **_kwargs):
            return {
                "indexed": "2026-01-01T00:00:00.000Z",
                "indexer_version_sni": "test-indexer",
                "diamm_latest_dt": "2026-01-01T00:00:00.000Z",
                "cantus_latest_dt": "2026-01-01T00:00:00.000Z",
            }

    mocker.patch("search_server.server.SolrConnection", FakeSolrConnection)

    _, resp = client.get("/about", headers={"Accept": "application/json"})
    assert_json_contract(
        resp,
        status=200,
        required_keys=[
            "id",
            "type",
            "serverVersion",
            "indexerVersion",
            "lastIndexed",
            "latestFromDIAMM",
            "latestFromCantus",
        ],
    )


@pytest.mark.endpoint
@pytest.mark.contract
def test_sitemap_routes_xml_contract(client, mocker):
    class FakeResults:
        def __init__(self):
            self.hits = 2
            self.docs = [
                {"id": "source_123", "type": "source", "updated": "2026-01-01"},
                {"id": "person_456", "type": "person", "updated": "2026-01-02"},
            ]

    class FakeSolrConnection:
        @staticmethod
        async def search(*_args, **_kwargs):
            return FakeResults()

    mocker.patch("search_server.routes.sitemap.SolrConnection", FakeSolrConnection)

    _, root_resp = client.get("/sitemap.xml")
    assert root_resp.status == 200
    assert_content_type(root_resp, "application/xml")
    assert "<sitemapindex" in root_resp.text

    _, page_resp = client.get("/sitemap-page-1.xml")
    assert page_resp.status == 200
    assert_content_type(page_resp, "application/xml")
    assert "<urlset" in page_resp.text
