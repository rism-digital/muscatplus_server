# ruff: noqa: S101

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import orjson
import pytest
from pyoxigraph import RdfFormat, parse

from search_server.request_handlers import handle_request, handle_search


class DummyApp:
    def __init__(self):
        self.ctx = SimpleNamespace(
            config={"common": {"debug": False, "muscat_auth": "token"}},
            context_uri=False,
            template_env=None,
        )


class DummyReq:
    def __init__(self, accept: str | None = None):
        self.headers = {}
        if accept is not None:
            self.headers["Accept"] = accept

        self.app = DummyApp()
        self.route = None
        self.match_info: dict[str, str] = {}
        self.ctx = SimpleNamespace(translations={})
        self.scheme = "https"
        self.host = "rism.online"


def run(coro):
    return asyncio.run(coro)


def json_body(resp):
    return orjson.loads(resp.body)


@pytest.mark.unit
@pytest.mark.contract
def test_handle_search_rejects_unsupported_accept():
    async def fake_handler(_req, **_kwargs):
        return {"ok": True}

    req = DummyReq(accept="application/xml")
    resp = run(handle_search(req, fake_handler))
    assert resp.status == 406
    assert json_body(resp)["message"].startswith("Accept header")


@pytest.mark.unit
@pytest.mark.contract
def test_handle_search_json_success_contract():
    async def fake_handler(_req, **_kwargs):
        return {"results": []}

    req = DummyReq(accept="application/json")
    resp = run(handle_search(req, fake_handler))
    assert resp.status == 200
    assert json_body(resp) == {"results": []}


@pytest.mark.unit
@pytest.mark.contract
def test_handle_request_not_found_contract(mocker):
    async def fake_handler(_req, **_kwargs):
        return None

    async def fake_tombstone(_req):
        return None

    mocker.patch("search_server.request_handlers.handle_tombstone", side_effect=fake_tombstone)
    req = DummyReq(accept="application/json")
    resp = run(handle_request(req, fake_handler))
    assert resp.status == 404
    assert json_body(resp)["type"] == "rism:NotFound"


@pytest.mark.unit
@pytest.mark.contract
def test_handle_request_tombstone_contract(mocker):
    async def fake_handler(_req, **_kwargs):
        return None

    async def fake_tombstone(_req):
        return {"type": "rism:Tombstone"}

    mocker.patch("search_server.request_handlers.handle_tombstone", side_effect=fake_tombstone)
    req = DummyReq(accept="application/json")
    resp = run(handle_request(req, fake_handler))
    assert resp.status == 410
    assert json_body(resp)["type"] == "rism:Tombstone"


@pytest.mark.unit
@pytest.mark.contract
def test_handle_request_html_branch(mocker):
    async def fake_handler(_req, **_kwargs):
        return {"id": "x"}

    mocker.patch("search_server.request_handlers.render_template", return_value="<html>ok</html>")

    req = DummyReq(accept="text/html")
    resp = run(handle_request(req, fake_handler))
    assert resp.status == 200
    assert "ok" in resp.body.decode()


@pytest.mark.unit
@pytest.mark.contract
def test_handle_request_raw_json_response(mocker):
    async def fake_handler(_req, **_kwargs):
        return {"id": "x"}

    async def fake_tombstone(_req):
        return None

    mocker.patch("search_server.request_handlers.handle_tombstone", side_effect=fake_tombstone)
    req = DummyReq(accept="application/json")
    resp = run(handle_request(req, fake_handler, raw_json_response=True))
    assert resp.status == 200
    assert json_body(resp) == {"id": "x"}


@pytest.mark.unit
@pytest.mark.contract
def test_handle_request_text_turtle_returns_turtle(mocker):
    async def fake_handler(_req, **_kwargs):
        return {
            "id": "https://rism.online/sources/1",
            "type": "rism:Source",
            "label": {"en": ["Example source"]},
        }

    async def fake_tombstone(_req):
        return None

    mocker.patch("search_server.request_handlers.handle_tombstone", side_effect=fake_tombstone)
    req = DummyReq(accept="text/turtle")

    resp = run(handle_request(req, fake_handler))
    body = resp.body.decode("utf-8")

    assert resp.status == 200
    assert resp.content_type == "text/turtle"
    assert "@prefix rism:" in body
    assert "rism:Source" in body
    assert set(
        parse(
            input=body.encode("utf-8"),
            format=RdfFormat.TURTLE,
            without_named_graphs=True,
        )
    )
