from __future__ import annotations

from dataclasses import dataclass

import pytest
from sanic import response

from tests.conftest import COVERED_ROUTE_PATHS, path_to_example


@dataclass
class FakeResults:
    hits: int
    docs: list[dict]


@pytest.fixture(autouse=True)
def mock_endpoint_boundaries(mocker):
    async def fake_handle_request(_req, _handler, **kwargs):
        return response.json({"ok": True, "kwargs": kwargs})

    async def fake_handle_search(_req, _handler, **kwargs):
        return response.json({"ok": True, "kwargs": kwargs})

    async def fake_front(_req):
        return response.html("<html><body>front</body></html>")

    async def fake_suggest(_req):
        return response.json({"results": []})

    async def fake_render(_req):
        return response.json({"rendered": True})

    async def fake_validate(_req):
        return response.json({"valid": True})

    async def fake_siglum_redirect(_req, _siglum):
        return "https://rism.online/institutions/123"

    async def fake_siglum_search(_req):
        return {"matches": []}

    async def fake_mei(_req, **_kwargs):
        return {"content": "<mei/>", "headers": {"content-type": "application/mei+xml"}}

    async def fake_png(_req, **_kwargs):
        return {"content": b"pngbytes", "headers": {"content-type": "image/png"}}

    class FakeOpenGraphSvg:
        def __init__(self, _record, context=None):
            self.serialized = {"title": "Test"}

    class FakeServerSolrConnection:
        @staticmethod
        async def get(_ident, **_kwargs):
            return {
                "indexed": "2026-01-01T00:00:00.000Z",
                "indexer_version_sni": "test-indexer",
                "diamm_latest_dt": "2026-01-01T00:00:00.000Z",
                "cantus_latest_dt": "2026-01-01T00:00:00.000Z",
            }

    class FakeSitemapSolrConnection:
        @staticmethod
        async def search(*_args, **_kwargs):
            return FakeResults(
                hits=2,
                docs=[
                    {"id": "source_123", "type": "source", "updated": "2026-01-01"},
                    {"id": "person_456", "type": "person", "updated": "2026-01-02"},
                ],
            )

    class FakeOgSolrConnection:
        @staticmethod
        async def get(_id, **_kwargs):
            return {"id": "source_123", "type": "source"}

    def fake_render_svg(_svg, outfile, _bin, _font):
        with open(outfile, "wb") as out:
            out.write(b"png")
        return True

    mocker.patch("search_server.server.handle_front_request", side_effect=fake_front)
    mocker.patch("search_server.server.SolrConnection", FakeServerSolrConnection)

    for patch_target in (
        "search_server.routes.countries.handle_request",
        "search_server.routes.external.handle_request",
        "search_server.routes.festivals.handle_request",
        "search_server.routes.institutions.handle_request",
        "search_server.routes.people.handle_request",
        "search_server.routes.places.handle_request",
        "search_server.routes.publications.handle_request",
        "search_server.routes.sources.handle_request",
        "search_server.routes.subjects.handle_request",
        "search_server.routes.works.handle_request",
    ):
        mocker.patch(patch_target, side_effect=fake_handle_request)

    for patch_target in (
        "search_server.routes.institutions.handle_search",
        "search_server.routes.people.handle_search",
        "search_server.routes.publications.handle_search",
        "search_server.routes.query.handle_search",
        "search_server.routes.sources.handle_search",
        "search_server.routes.subjects.handle_search",
        "search_server.routes.works.handle_search",
    ):
        mocker.patch(patch_target, side_effect=fake_handle_search)

    mocker.patch("search_server.routes.query.handle_suggest_request", side_effect=fake_suggest)
    mocker.patch("search_server.routes.incipits.handle_incipit_render", side_effect=fake_render)
    mocker.patch("search_server.routes.incipits.handle_incipit_validate", side_effect=fake_validate)
    mocker.patch(
        "search_server.routes.sigla.handle_institution_sigla_request",
        side_effect=fake_siglum_redirect,
    )
    mocker.patch(
        "search_server.routes.sigla.handle_siglum_search_request",
        side_effect=fake_siglum_search,
    )
    mocker.patch("search_server.routes.sources.handle_mei_download", side_effect=fake_mei)
    mocker.patch("search_server.routes.sources.handle_png_download", side_effect=fake_png)
    mocker.patch("search_server.routes.works.handle_mei_download", side_effect=fake_mei)
    mocker.patch("search_server.routes.works.handle_png_download", side_effect=fake_png)
    mocker.patch("search_server.routes.sitemap.SolrConnection", FakeSitemapSolrConnection)
    mocker.patch("search_server.routes.opengraph.SolrConnection", FakeOgSolrConnection)
    mocker.patch("search_server.routes.opengraph.OpenGraphSvg", FakeOpenGraphSvg)
    mocker.patch("search_server.routes.opengraph.render_svg", side_effect=fake_render_svg)


NOT_IMPLEMENTED_PATHS = {
    "countries/<country_id:str>",
    "external/<project:str>/source/<source_id:str>/holding/<institution_id:str>",
    "incipits/<incipit_id:str>",
    "institutions",
    "institutions/<institution_id:str>/digital-objects",
    "institutions/<institution_id:str>/digital-objects/<dobject_id:str>",
    "institutions/<institution_id:str>/relationships",
    "institutions/<institution_id:str>/relationships/<relationship_id:str>",
    "people",
    "people/<person_id:str>/digital-objects",
    "people/<person_id:str>/digital-objects/<dobject_id:str>",
    "people/<person_id:str>/relationships",
    "people/<person_id:str>/relationships/<relationship_id:str>",
    "places",
    "places/<place_id:str>/relationships/<relationship_id:str>",
    "sources/<source_id:str>/creator",
    "sources/<source_id:str>/digital-objects",
    "sources/<source_id:str>/digital-objects/<dobject_id:str>",
    "sources/<source_id:str>/holdings/<holding_id:str>/digital-objects",
    "sources/<source_id:str>/holdings/<holding_id:str>/digital-objects/<dobject_id:str>",
    "sources/<source_id:str>/holdings/<holding_id:str>/relationships",
    "sources/<source_id:str>/inventory-items",
    "sources/<source_id:str>/inventory-items/<inventory_item_id:str>",
    "sources/<source_id:str>/material-groups",
    "sources/<source_id:str>/material-groups/<mg_id:str>",
    "sources/<source_id:str>/material-groups/<mg_id:str>/relationships",
    "sources/<source_id:str>/relationships",
    "sources/<source_id:str>/relationships/<relationship_id:str>",
    "subjects",
    "works/<work_id:str>/incipits",
    "works/<work_id:str>/incipits/<work_num:str>",
}


@pytest.mark.endpoint
def test_route_inventory_matches_registry(app):
    actual_paths = {route.path for route in app.router.routes_all.values()}
    assert actual_paths == COVERED_ROUTE_PATHS


@pytest.mark.endpoint
@pytest.mark.parametrize("route_path", sorted(COVERED_ROUTE_PATHS))
def test_all_registered_routes_smoke(client, route_path: str):
    url = path_to_example(route_path)
    if route_path == "sigla/<siglum:str>":
        _, resp = client.get(url, allow_redirects=False)
    else:
        _, resp = client.get(url)

    if route_path in NOT_IMPLEMENTED_PATHS:
        assert resp.status == 501
        return

    if route_path == "sigla/<siglum:str>":
        assert resp.status == 303
        assert "location" in resp.headers
        return

    assert resp.status < 500, f"{route_path} returned {resp.status}"
