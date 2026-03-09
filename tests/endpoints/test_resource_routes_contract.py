from __future__ import annotations

import pytest
from sanic import response


REQUEST_ROUTE_CASES = [
    (
        "search_server.routes.external.handle_request",
        "/external/diamm/person/ext-1",
        "handle_external_request",
        {"project": "diamm", "resource_type": "person", "ext_id": "ext-1"},
    ),
    (
        "search_server.routes.countries.handle_request",
        "/countries/list",
        "handle_country_list_request",
        {"raw_json_response": True},
    ),
    (
        "search_server.routes.festivals.handle_request",
        "/festivals/123",
        "handle_festival_request",
        {"festival_id": "123"},
    ),
    (
        "search_server.routes.institutions.handle_request",
        "/institutions/123",
        "handle_institution_request",
        {"institution_id": "123"},
    ),
    (
        "search_server.routes.institutions.handle_request",
        "/institutions/123/location.geojson",
        "handle_institution_geojson_request",
        {"institution_id": "123", "suppress_context": True, "raw_json_response": True},
    ),
    (
        "search_server.routes.people.handle_request",
        "/people/123",
        "handle_person_request",
        {"person_id": "123"},
    ),
    (
        "search_server.routes.places.handle_request",
        "/places/123",
        "handle_place_request",
        {"place_id": "123"},
    ),
    (
        "search_server.routes.publications.handle_request",
        "/publications/123",
        "handle_publication_request",
        {"publication_id": "123"},
    ),
    (
        "search_server.routes.publications.handle_request",
        "/publications",
        "handle_publication_list_request",
        {},
    ),
    (
        "search_server.routes.sources.handle_request",
        "/sources/123",
        "handle_source_request",
        {"source_id": "123"},
    ),
    (
        "search_server.routes.sources.handle_request",
        "/sources/123/incipits",
        "handle_incipits_list_request",
        {"source_id": "123"},
    ),
    (
        "search_server.routes.sources.handle_request",
        "/sources/123/incipits/1",
        "handle_incipit_request",
        {"record_id": "123", "record_type": "source", "work_num": "1"},
    ),
    (
        "search_server.routes.sources.handle_request",
        "/sources/123/holdings",
        "handle_exemplar_section_request",
        {"source_id": "123"},
    ),
    (
        "search_server.routes.sources.handle_request",
        "/sources/123/holdings/321",
        "handle_holdings_request",
        {"source_id": "123", "holding_id": "321"},
    ),
    (
        "search_server.routes.subjects.handle_request",
        "/subjects/123",
        "handle_subject_request",
        {"subject_id": "123"},
    ),
    (
        "search_server.routes.works.handle_request",
        "/works/123",
        "handle_work_request",
        {"work_id": "123"},
    ),
]


SEARCH_ROUTE_CASES = [
    (
        "search_server.routes.query.handle_search",
        "/search",
        "handle_search_request",
        {},
    ),
    (
        "search_server.routes.query.handle_search",
        "/probe",
        "handle_probe_request",
        {},
    ),
    (
        "search_server.routes.people.handle_search",
        "/people/123/sources",
        "handle_person_search_request",
        {"person_id": "123"},
    ),
    (
        "search_server.routes.people.handle_search",
        "/people/123/probe",
        "handle_person_probe_request",
        {"person_id": "123"},
    ),
    (
        "search_server.routes.institutions.handle_search",
        "/institutions/123/sources",
        "handle_institution_search_request",
        {"institution_id": "123"},
    ),
    (
        "search_server.routes.institutions.handle_search",
        "/institutions/123/probe",
        "handle_institution_probe_request",
        {"institution_id": "123"},
    ),
    (
        "search_server.routes.publications.handle_search",
        "/publications/123/works",
        "handle_publication_search_request",
        {"publication_id": "123"},
    ),
    (
        "search_server.routes.sources.handle_search",
        "/sources/123/contents",
        "handle_contents_search_request",
        {"source_id": "123"},
    ),
    (
        "search_server.routes.sources.handle_search",
        "/sources/123/probe",
        "handle_contents_probe_request",
        {"source_id": "123"},
    ),
    (
        "search_server.routes.subjects.handle_search",
        "/subjects/123/sources",
        "handle_subject_source_request",
        {"subject_id": "123"},
    ),
    (
        "search_server.routes.works.handle_search",
        "/works/123/sources",
        "handle_work_search_request",
        {"work_id": "123"},
    ),
    (
        "search_server.routes.works.handle_search",
        "/works/123/probe",
        "handle_work_probe_request",
        {"work_id": "123"},
    ),
]


@pytest.mark.endpoint
@pytest.mark.contract
@pytest.mark.parametrize(
    ("patch_target", "path", "expected_handler_name", "expected_kwargs"),
    REQUEST_ROUTE_CASES,
)
def test_handle_request_routes_contract(
    client, mocker, patch_target: str, path: str, expected_handler_name: str, expected_kwargs: dict
):
    seen: dict = {}

    async def fake(req, handler, **kwargs):
        seen["handler_name"] = handler.__name__
        seen["kwargs"] = kwargs
        return response.json({"ok": True, "kwargs": kwargs})

    stub = mocker.patch(patch_target, side_effect=fake)
    _, resp = client.get(path)

    assert resp.status == 200
    assert resp.json["ok"] is True
    assert seen["handler_name"] == expected_handler_name
    assert seen["kwargs"] == expected_kwargs
    assert stub.call_count == 1


@pytest.mark.endpoint
@pytest.mark.contract
@pytest.mark.parametrize(
    ("patch_target", "path", "expected_handler_name", "expected_kwargs"),
    SEARCH_ROUTE_CASES,
)
def test_handle_search_routes_contract(
    client, mocker, patch_target: str, path: str, expected_handler_name: str, expected_kwargs: dict
):
    seen: dict = {}

    async def fake(req, handler, **kwargs):
        seen["handler_name"] = handler.__name__
        seen["kwargs"] = kwargs
        return response.json({"ok": True, "kwargs": kwargs})

    stub = mocker.patch(patch_target, side_effect=fake)
    _, resp = client.get(path)

    assert resp.status == 200
    assert resp.json["ok"] is True
    assert seen["handler_name"] == expected_handler_name
    assert seen["kwargs"] == expected_kwargs
    assert stub.call_count == 1
