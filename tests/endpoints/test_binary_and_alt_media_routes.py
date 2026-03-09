from __future__ import annotations

import pytest
from sanic import response

from tests.conftest import assert_content_type


@pytest.mark.endpoint
@pytest.mark.contract
def test_source_incipit_content_negotiation(client, mocker):
    async def fake_mei(_req, **_kwargs):
        return {"content": "<mei/>", "headers": {"content-type": "application/mei+xml"}}

    async def fake_png(_req, **_kwargs):
        return {"content": b"\x89PNG\r\n", "headers": {"content-type": "image/png"}}

    mocker.patch("search_server.routes.sources.handle_mei_download", side_effect=fake_mei)
    mocker.patch("search_server.routes.sources.handle_png_download", side_effect=fake_png)

    _, mei_resp = client.get("/sources/123/incipits/1", headers={"Accept": "application/mei+xml"})
    assert mei_resp.status == 200
    assert_content_type(mei_resp, "application/mei+xml")
    assert "<mei/>" in mei_resp.text

    _, png_resp = client.get("/sources/123/incipits/1", headers={"Accept": "image/png"})
    assert png_resp.status == 200
    assert_content_type(png_resp, "image/png")
    assert png_resp.body.startswith(b"\x89PNG")


@pytest.mark.endpoint
@pytest.mark.contract
@pytest.mark.parametrize(
    ("path", "patch_target", "content_type"),
    [
        ("/sources/123/incipits/1/mei", "search_server.routes.sources.handle_mei_download", "application/mei+xml"),
        ("/sources/123/incipits/1/png", "search_server.routes.sources.handle_png_download", "image/png"),
        ("/works/123/incipits/1/mei", "search_server.routes.works.handle_mei_download", "application/mei+xml"),
        ("/works/123/incipits/1/png", "search_server.routes.works.handle_png_download", "image/png"),
        (
            "/sources/123/inventory-items/654/incipits/1/mei",
            "search_server.routes.sources.handle_mei_download",
            "application/mei+xml",
        ),
        (
            "/sources/123/inventory-items/654/incipits/1/png",
            "search_server.routes.sources.handle_png_download",
            "image/png",
        ),
    ],
)
def test_suffix_media_routes(client, mocker, path: str, patch_target: str, content_type: str):
    async def fake_media(_req, **_kwargs):
        if content_type == "application/mei+xml":
            return {"content": "<mei/>", "headers": {"content-type": content_type}}
        return {"content": b"\x89PNG\r\n", "headers": {"content-type": content_type}}

    mocker.patch(patch_target, side_effect=fake_media)
    _, resp = client.get(path)
    assert resp.status == 200
    assert_content_type(resp, content_type)


@pytest.mark.endpoint
@pytest.mark.contract
def test_incipit_render_and_validate_routes(client, mocker):
    async def fake_render(_req):
        return response.json({"rendered": True})

    async def fake_validate(_req):
        return response.json({"valid": True})

    mocker.patch("search_server.routes.incipits.handle_incipit_render", side_effect=fake_render)
    mocker.patch("search_server.routes.incipits.handle_incipit_validate", side_effect=fake_validate)

    _, render_resp = client.get("/incipits/render")
    assert render_resp.status == 200
    assert render_resp.json == {"rendered": True}

    _, validate_resp = client.get("/incipits/validate")
    assert validate_resp.status == 200
    assert validate_resp.json == {"valid": True}


@pytest.mark.endpoint
@pytest.mark.contract
def test_sigla_routes(client, mocker):
    async def fake_redirect(_req, _siglum):
        return "https://rism.online/institutions/123"

    async def fake_search(_req):
        return {"matches": [{"id": "123"}]}

    mocker.patch(
        "search_server.routes.sigla.handle_institution_sigla_request",
        side_effect=fake_redirect,
    )
    mocker.patch(
        "search_server.routes.sigla.handle_siglum_search_request",
        side_effect=fake_search,
    )

    _, redirect_resp = client.get("/sigla/US-NYp", allow_redirects=False)
    assert redirect_resp.status == 303
    assert redirect_resp.headers["location"].endswith("/institutions/123")

    _, search_resp = client.get("/sigla")
    assert search_resp.status == 200
    assert search_resp.json == {"matches": [{"id": "123"}]}


@pytest.mark.endpoint
@pytest.mark.contract
def test_opengraph_image_route(client, mocker):
    class FakeOpenGraphSvg:
        def __init__(self, _record, context=None):
            self.serialized = {"title": "Test"}

    class FakeSolrConnection:
        @staticmethod
        async def get(_id, **_kwargs):
            return {"id": "source_123", "type": "source"}

    def fake_render_svg(_svg, outfile, _bin, _font):
        with open(outfile, "wb") as out:
            out.write(b"\x89PNG\r\n")
        return True

    mocker.patch("search_server.routes.opengraph.SolrConnection", FakeSolrConnection)
    mocker.patch("search_server.routes.opengraph.OpenGraphSvg", FakeOpenGraphSvg)
    mocker.patch("search_server.routes.opengraph.render_svg", side_effect=fake_render_svg)

    _, resp = client.get("/og/img/source_123.png")
    assert resp.status == 200
    assert_content_type(resp, "image/png")
    assert resp.body.startswith(b"\x89PNG")
