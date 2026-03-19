from __future__ import annotations

import json

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, Namespace
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
def test_person_context_expands_semantic_sections(client):
    _, ctx_resp = client.get("/api/v1/person.json")
    assert_json_contract(ctx_resp, status=200, required_keys=["@context"])
    person_context = ctx_resp.json["@context"]

    person_doc = {
        "@context": person_context,
        "id": "https://rism.online/people/115324",
        "type": "rism:Person",
        "label": {"none": ["Mozart, Wolfgang Amadeus (1756-1791)"]},
        "recordHistory": {
            "type": "rism:RecordHistory",
            "created": {
                "label": {"en": ["Created on"]},
                "value": "2016-11-09T00:00:00Z",
            },
            "updated": {
                "label": {"en": ["Last modification"]},
                "value": "2026-01-15T09:37:34Z",
            },
        },
        "biographicalDetails": {
            "sectionLabel": {"en": ["Biographical details"]},
            "summary": [
                {
                    "label": {"en": ["Life dates"]},
                    "value": {"none": ["1756-1791"]},
                }
            ],
        },
        "relationships": {
            "items": [
                {
                    "role": {
                        "label": {"en": ["Father of"]},
                        "value": "father of",
                        "id": "https://rism.online/vocabulary/relationship/father_of",
                    },
                    "relatedTo": {
                        "id": "https://rism.online/people/276624",
                        "label": {"none": ["Mozart, Franz Xaver Wolfgang (1791-1844)"]},
                        "type": "rism:Person",
                    },
                }
            ]
        },
        "works": {
            "sectionLabel": {"en": ["Works"]},
            "workReferences": {
                "type": "rism:ExternalWorkReferencesSection",
                "items": [
                    {
                        "value": "Ave Verum Corpus",
                        "type": "rism:WorkNode",
                        "search": "https://rism.online/search?fq=work-node%3Adnb%3A300107153",
                        "url": "https://d-nb.info/gnd/300107153",
                    }
                ],
            },
        },
        "sources": {
            "url": "https://rism.online/people/115324/sources",
            "totalItems": 19113,
        },
    }

    graph = Graph()
    graph.parse(data=json.dumps(person_doc), format="json-ld")

    subject = URIRef("https://rism.online/people/115324")
    rism = Namespace("https://rism.online/api/v1#")
    dcterms = Namespace("http://purl.org/dc/terms/")

    predicates = {str(pred) for pred in graph.predicates()}
    assert len(predicates) > 6
    assert (subject, RDF.type, rism.Person) in graph
    assert sum(1 for _ in graph.objects(subject, RDFS.label)) == 1

    # Verify explicit mapping for record history and relationships.
    assert any(graph.objects(subject, rism.recordHistory))
    relationship_nodes = list(graph.objects(subject, rism.hasRelationship))
    assert relationship_nodes
    assert any(graph.objects(relationship_nodes[0], rism.hasRole))
    assert any(graph.objects(relationship_nodes[0], dcterms.relation))


@pytest.mark.endpoint
@pytest.mark.contract
def test_institution_context_expands_semantic_sections(client):
    _, ctx_resp = client.get("/api/v1/institution.json")
    assert_json_contract(ctx_resp, status=200, required_keys=["@context"])
    institution_context = ctx_resp.json["@context"]

    institution_doc = {
        "@context": institution_context,
        "id": "https://rism.online/institutions/30000042",
        "type": "rism:Institution",
        "typeLabel": {"en": ["Institution"]},
        "label": {"none": ["Example Institution"]},
        "organizationDetails": {
            "sectionLabel": {"en": ["Summary"]},
            "summary": [
                {
                    "label": {"en": ["Siglum"]},
                    "value": {"none": ["D-Dl"]},
                }
            ],
        },
        "recordHistory": {
            "type": "rism:RecordHistory",
            "created": {
                "label": {"en": ["Created on"]},
                "value": "2016-11-09T00:00:00Z",
            },
            "updated": {
                "label": {"en": ["Last modification"]},
                "value": "2025-06-20T05:19:52Z",
            },
        },
        "location": {
            "type": "rism:LocationAddressSection",
            "label": {"en": ["Location and address"]},
            "coordinates": {
                "id": "https://rism.online/institutions/30000042/location.geojson",
                "sectionLabel": {"en": ["Location"]},
                "type": "geojson:Feature",
                "geometry": {
                    "type": "geojson:Point",
                    "coordinates": [13.73, 51.02],
                },
            },
        },
        "sources": {
            "url": "https://rism.online/institutions/30000042/sources",
            "totalItems": 71910,
        },
        "relationships": {
            "sectionLabel": {"en": ["Relations"]},
            "items": [
                {
                    "role": {
                        "label": {"en": ["Includes holdings from"]},
                        "value": "contained-by",
                        "id": "https://rism.online/vocabulary/relationship/contained_by",
                    },
                    "relatedTo": {
                        "id": "https://rism.online/institutions/30000037",
                        "label": {"none": ["Related Institution"]},
                        "type": "rism:Institution",
                    },
                }
            ],
        },
        "properties": {
            "siglum": "D-Dl",
            "countryCodes": ["D"],
            "city": "Dresden",
        },
    }

    graph = Graph()
    graph.parse(data=json.dumps(institution_doc), format="json-ld")

    subject = URIRef("https://rism.online/institutions/30000042")
    rism = Namespace("https://rism.online/api/v1#")
    dcterms = Namespace("http://purl.org/dc/terms/")

    predicates = {str(pred) for pred in graph.predicates()}
    assert len(predicates) > 10
    assert (subject, RDF.type, rism.Institution) in graph
    assert sum(1 for _ in graph.objects(subject, RDFS.label)) == 1
    assert any(graph.objects(subject, rism.organizationDetails))
    assert any(graph.objects(subject, rism.recordHistory))
    assert any(graph.objects(subject, rism.hasLocation))
    assert any(graph.objects(subject, rism.sources))

    relationship_nodes = list(graph.objects(subject, rism.hasRelationship))
    assert relationship_nodes
    assert any(graph.objects(relationship_nodes[0], rism.hasRole))
    assert any(graph.objects(relationship_nodes[0], dcterms.relation))


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
