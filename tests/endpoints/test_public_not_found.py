# ruff: noqa: S101
import json
import re
from unittest.mock import AsyncMock

import pytest


@pytest.mark.parametrize(
    ("accept", "content_type"),
    [
        ("*/*", "text/html"),
        ("text/html", "text/html"),
        ("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "text/html"),
        ("application/json, */*", "application/json"),
        ("application/ld+json", "application/json"),
        ("text/html;q=0.2, application/json;q=0.9", "application/json"),
        ("text/html;q=0, */*", "application/json"),
        ("image/png", None),
    ],
)
def test_unknown_public_url_negotiates_404(client, accept, content_type):
    _, resp = client.get("/not-a-public-route", headers={"Accept": accept})

    assert resp.status == 404
    assert resp.headers["vary"] == "Accept"
    assert resp.headers["cache-control"] == "no-store"
    if content_type is None:
        assert resp.body == b""
        return

    assert resp.headers["content-type"].split(";")[0] == content_type
    if content_type == "text/html":
        assert 'src="/static/app.js"' in resp.text
        assert "initialData: null" in resp.text
        assert "countryList: null" in resp.text
    else:
        assert "not found" in resp.json["message"]


def test_public_not_found_uses_site_metadata_without_canonical_url(client):
    _, resp = client.get("/not-a-public-route", headers={"Accept": "text/html"})

    assert resp.status == 404
    assert 'rel="canonical"' not in resp.text
    script = re.search(r'<script type="application/ld\+json">(.*?)</script>', resp.text, re.S)
    assert script is not None
    metadata = json.loads(script[1])
    assert metadata["@type"] == "WebSite"
    assert "@id" not in metadata
    assert metadata["name"] == "RISM Online"
    assert metadata["maintainer"]["name"] == "RISM Digital"
    assert f'name="description" content="{metadata["description"]}"' in resp.text


def test_missing_record_shell_and_json_follow_up(client, mocker):
    mocker.patch(
        "search_server.routes.people.handle_person_request",
        new_callable=AsyncMock,
        return_value=None,
    )
    mocker.patch(
        "search_server.request_handlers.handle_tombstone",
        new_callable=AsyncMock,
        return_value=None,
    )

    _, html = client.get("/people/123", headers={"Accept": "text/html"})
    assert html.status == 404
    assert html.headers["content-type"].startswith("text/html")
    assert html.headers["cache-control"] == "no-store"
    assert "initialData: null" in html.text

    _, data = client.get("/people/123", headers={"Accept": "application/ld+json"})
    assert data.status == 404
    assert data.headers["content-type"].startswith("application/json")
    assert data.json["type"] == "rism:NotFound"


def test_unknown_api_url_keeps_json_error(client):
    _, resp = client.get("/api/v1/not-a-route", headers={"Accept": "text/html"})

    assert resp.status == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert "not found" in resp.json["message"]


def test_missing_explicit_download_keeps_json_error(client, mocker):
    mocker.patch(
        "search_server.routes.sources.handle_mei_download",
        new_callable=AsyncMock,
        return_value=None,
    )
    _, resp = client.get("/sources/123/incipits/1/mei", headers={"Accept": "text/html"})

    assert resp.status == 404
    assert resp.headers["content-type"].startswith("application/json")
