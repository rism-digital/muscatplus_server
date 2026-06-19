from __future__ import annotations

import re
from collections.abc import Iterable

import pytest

from search_server.server import app as sanic_app


COVERED_ROUTE_PATHS: set[str] = {
    "",
    "<page_num:sitemap-page-(?P<page_num>\\d+)\\.xml>",
    "about",
    "api/v1/context.json",
    "api/v1/institution.json",
    "api/v1/place.json",
    "api/v1/person.json",
    "api/v1/publication.json",
    "api/v1/source.json",
    "api/v1/work.json",
    "countries/<country_id:str>",
    "countries/list",
    "external/<project:str>/<resource_type:str>/<ext_id:str>",
    "external/<project:str>/source/<source_id:str>/holding/<institution_id:str>",
    "festivals/<festival_id:str>",
    "incipits/<incipit_id:str>",
    "incipits/render",
    "incipits/validate",
    "institutions",
    "institutions/<institution_id:str>",
    "institutions/<institution_id:str>/digital-objects",
    "institutions/<institution_id:str>/digital-objects/<dobject_id:str>",
    "institutions/<institution_id:str>/external-authorities",
    "institutions/<institution_id:str>/external-authorities/<authority_id:str>",
    "institutions/<institution_id:str>/location.geojson",
    "institutions/<institution_id:str>/notes",
    "institutions/<institution_id:str>/probe",
    "institutions/<institution_id:str>/relationships",
    "institutions/<institution_id:str>/relationships/<relationship_id:str>",
    "institutions/<institution_id:str>/sources",
    "og/img/<image_name:str>",
    "people",
    "people/<person_id:str>",
    "people/<person_id:str>/digital-objects",
    "people/<person_id:str>/digital-objects/<dobject_id:str>",
    "people/<person_id:str>/external-authorities",
    "people/<person_id:str>/external-authorities/<authority_id:str>",
    "people/<person_id:str>/notes",
    "people/<person_id:str>/probe",
    "people/<person_id:str>/relationships",
    "people/<person_id:str>/relationships/<relationship_id:str>",
    "people/<person_id:str>/sources",
    "places",
    "places/<place_id:str>",
    "places/<place_id:str>/external-authorities",
    "places/<place_id:str>/external-authorities/<authority_id:str>",
    "places/<place_id:str>/relationships/<relationship_id:str>",
    "probe",
    "publications",
    "publications/<publication_id:str>",
    "publications/<publication_id:str>/notes",
    "publications/<publication_id:str>/relationships",
    "publications/<publication_id:str>/relationships/<relationship_id:str>",
    "publications/<publication_id:str>/works",
    "search",
    "sigla",
    "sigla/<siglum:str>",
    "sitemap.xml",
    "sources/<source_id:str>",
    "sources/<source_id:str>/contents",
    "sources/<source_id:str>/creator",
    "sources/<source_id:str>/digital-objects",
    "sources/<source_id:str>/digital-objects/<dobject_id:str>",
    "sources/<source_id:str>/holdings",
    "sources/<source_id:str>/holdings/<holding_id:str>",
    "sources/<source_id:str>/holdings/<holding_id:str>/digital-objects",
    "sources/<source_id:str>/holdings/<holding_id:str>/digital-objects/<dobject_id:str>",
    "sources/<source_id:str>/holdings/<holding_id:str>/relationships",
    "sources/<source_id:str>/holdings/<holding_id:str>/relationships/<relationship_id:str>",
    "sources/<source_id:str>/incipits",
    "sources/<source_id:str>/incipits/<work_num:str>",
    "sources/<source_id:str>/incipits/<work_num:str>/mei",
    "sources/<source_id:str>/incipits/<work_num:str>/png",
    "sources/<source_id:str>/inventory-items",
    "sources/<source_id:str>/inventory-items/probe",
    "sources/<source_id:str>/inventory-items/<inventory_item_id:str>",
    "sources/<source_id:str>/inventory-items/<inventory_item_id:str>/incipits/<work_num:str>/mei",
    "sources/<source_id:str>/inventory-items/<inventory_item_id:str>/incipits/<work_num:str>/png",
    "sources/<source_id:str>/inventory-items/<inventory_item_id:str>/liturgical-festivals",
    "sources/<source_id:str>/inventory-items/<inventory_item_id:str>/performance-locations",
    "sources/<source_id:str>/inventory-items/<inventory_item_id:str>/references-notes",
    "sources/<source_id:str>/inventory-items/<inventory_item_id:str>/relationships",
    "sources/<source_id:str>/inventory-items/<inventory_item_id:str>/relationships/<relationship_id:str>",
    "sources/<source_id:str>/liturgical-festivals",
    "sources/<source_id:str>/material-groups",
    "sources/<source_id:str>/material-groups/<mg_id:str>",
    "sources/<source_id:str>/material-groups/<mg_id:str>/relationships",
    "sources/<source_id:str>/material-groups/<mg_id:str>/relationships/<relationship_id:str>",
    "sources/<source_id:str>/performance-locations",
    "sources/<source_id:str>/probe",
    "sources/<source_id:str>/references-notes",
    "sources/<source_id:str>/relationships",
    "sources/<source_id:str>/relationships/<relationship_id:str>",
    "subjects",
    "subjects/<subject_id:str>",
    "subjects/<subject_id:str>/sources",
    "suggest",
    "works/<work_id:str>",
    "works/<work_id:str>/external-authorities",
    "works/<work_id:str>/external-authorities/<authority_id:str>",
    "works/<work_id:str>/incipits",
    "works/<work_id:str>/incipits/<work_num:str>",
    "works/<work_id:str>/incipits/<work_num:str>/mei",
    "works/<work_id:str>/incipits/<work_num:str>/png",
    "works/<work_id:str>/liturgical-festivals",
    "works/<work_id:str>/performance-locations",
    "works/<work_id:str>/probe",
    "works/<work_id:str>/references-notes",
    "works/<work_id:str>/relationships",
    "works/<work_id:str>/relationships/<relationship_id:str>",
    "works/<work_id:str>/sources",
}


def assert_content_type(resp, expected_prefix: str) -> None:
    content_type = resp.headers.get("content-type", "").lower()
    assert content_type.startswith(expected_prefix.lower())


def assert_json_contract(resp, status: int, required_keys: Iterable[str]) -> None:
    assert resp.status == status
    assert_content_type(resp, "application/json")
    body = resp.json
    assert isinstance(body, dict)
    for key in required_keys:
        assert key in body


def path_to_example(path: str) -> str:
    if path == "":
        return "/"
    if path.startswith("<page_num:sitemap-page-"):
        return "/sitemap-page-1.xml"

    replacements = {
        "source_id": "123",
        "person_id": "123",
        "institution_id": "123",
        "work_id": "123",
        "publication_id": "123",
        "place_id": "123",
        "subject_id": "123",
        "festival_id": "123",
        "country_id": "CH",
        "relationship_id": "999",
        "dobject_id": "456",
        "holding_id": "321",
        "inventory_item_id": "654",
        "mg_id": "88",
        "work_num": "1",
        "project": "diamm",
        "resource_type": "person",
        "ext_id": "ext-1",
        "authority_id": "auth-1",
        "siglum": "US-NYp",
        "image_name": "source_123.png",
        "incipit_id": "inc-1",
    }

    def _repl(match: re.Match[str]) -> str:
        name = match.group(1)
        return replacements.get(name, "x")

    concrete = re.sub(r"<([^:>]+):[^>]+>", _repl, path)
    return f"/{concrete}"


@pytest.fixture
def app():
    return sanic_app


@pytest.fixture
def client(app):
    return app.test_client
