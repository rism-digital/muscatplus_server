# ruff: noqa: S101
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import orjson
import pytest

from search_server import request_handlers as handlers
from search_server import server
from search_server.resources.front import front
from tests.handlers.test_request_handlers_contract import DummyReq


@pytest.mark.parametrize(
    "accept",
    [
        None,
        "",
        "*/*",
        "text/html",
        "application/xml",
        "application/not-json",
        "text/html,application/xhtml+xml,application/json",
        "application/json,text/html;q=0",
        "application/json,*/*",
        "application/json,text/html-extra",
        "application/json",
        "application/ld+json",
        "application/ld+json;profile=other;q=0.5",
    ],
)
@pytest.mark.parametrize("endpoint", ["record", "search", "front", "about"])
def test_representation(accept, endpoint, mocker):
    req = DummyReq(accept)
    req.app.ctx.config["common"]["version"] = "test"
    data = {"id": "example", "type": "rism:Source"}
    html = "<html>representation</html>"
    renderer = mocker.patch(
        "search_server.request_handlers.render_template", return_value=html
    )
    mocker.patch("search_server.server.render_template", return_value=html)
    mocker.patch(
        "search_server.resources.front.front.render_template", return_value=html
    )
    mocker.patch.object(front, "SearchRequest")
    mocker.patch.object(
        front, "SolrConnection", SimpleNamespace(search=AsyncMock(return_value={}))
    )
    mocker.patch.object(front, "Front", return_value=SimpleNamespace(serialized=data))
    mocker.patch.object(
        server, "SolrConnection", SimpleNamespace(get=AsyncMock(return_value=None))
    )
    mocker.patch.object(server, "get_identifier", return_value="example")
    calls = {
        "record": lambda: handlers.handle_request(
            req, AsyncMock(return_value=data), suppress_context=True
        ),
        "search": lambda: handlers.handle_search(req, AsyncMock(return_value=data)),
        "front": lambda: front.handle_front_request(req),
        "about": lambda: server.about(req),
    }
    resp = asyncio.run(calls[endpoint]())
    wants_json = accept in [
        "application/json",
        "application/ld+json",
        "application/ld+json;profile=other;q=0.5",
        "application/json,text/html-extra",
    ]
    assert resp.status == 200
    if wants_json:
        body = orjson.loads(resp.body)
        if endpoint == "about":
            assert body["type"] == "rism:About"
            assert body["serverVersion"] == "test"
        else:
            assert body == data
    else:
        assert resp.content_type.startswith("text/html")
        assert resp.body.decode() == html
        if endpoint in ("record", "search"):
            renderer.assert_called_once_with(req.app.ctx, req, data)


@pytest.mark.parametrize(
    ("accept", "serializer", "content_type"),
    [
        ("text/turtle;q=0.2", "to_turtle", "text/turtle"),
        ("application/n-triples;q=1", "to_ntriples", "application/n-triples"),
        (
            "application/ld+json;profile=expanded",
            "to_expanded_jsonld",
            handlers.EXPANDED_JSONLD_MEDIA_TYPE,
        ),
        (
            "application/ld+json;q=0.5; profile=expanded",
            "to_expanded_jsonld",
            handlers.EXPANDED_JSONLD_MEDIA_TYPE,
        ),
    ],
)
def test_record_serializers(accept, serializer, content_type, mocker):
    convert = mocker.patch.object(handlers, serializer, return_value="serialized")
    resp = asyncio.run(
        handlers.handle_request(DummyReq(accept), AsyncMock(return_value={"id": "x"}))
    )
    assert resp.content_type == content_type
    assert resp.body == b"serialized"
    assert "@context" in convert.call_args.args[0]


def test_marcxml(mocker):
    req = DummyReq("application/marcxml+xml;q=1")
    req.match_info = {"source_id": "123"}
    builder = mocker.patch.object(handlers, "ClientBuilder")
    client = builder.return_value.default_headers.return_value.build.return_value.__aenter__.return_value
    client.get = mocker.Mock()
    client.get.return_value.build.return_value.send = AsyncMock(
        return_value=SimpleNamespace(
            status=200, text=AsyncMock(return_value="<record/>")
        )
    )
    resp = asyncio.run(
        handlers.handle_request(req, AsyncMock(return_value={"id": "x"}))
    )
    assert resp.content_type == handlers.MARCXML_MEDIA_TYPE
    assert resp.body == b"<record/>"
    client.get.assert_called_once_with("https://muscat.rism.info/data/sources/123")


@pytest.mark.parametrize("accept", [None, "*/*", "text/html"])
def test_raw_json_override(accept):
    resp = asyncio.run(
        handlers.handle_request(
            DummyReq(accept),
            AsyncMock(return_value={"id": "x"}),
            raw_json_response=True,
        )
    )
    assert orjson.loads(resp.body) == {"id": "x"}


def test_profile_must_belong_to_jsonld():
    assert not handlers.accepts(
        "application/json;profile=expanded", handlers.EXPANDED_JSONLD_MEDIA_TYPE
    )
    assert not handlers.accepts("application/not-json", handlers.JSON_MEDIA_TYPE)
