from __future__ import annotations

import json

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, XSD, Namespace
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
def test_api_contexts_do_not_use_generic_has_item_predicates(client):
    def iter_context_values(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from iter_context_values(child)
        elif isinstance(value, list):
            for child in value:
                yield from iter_context_values(child)

    for path in [
        "/api/v1/person.json",
        "/api/v1/institution.json",
        "/api/v1/work.json",
        "/api/v1/publication.json",
        "/api/v1/source.json",
    ]:
        _, resp = client.get(path)
        assert_json_contract(resp, status=200, required_keys=["@context"])

        ids = {
            value.get("@id")
            for value in iter_context_values(resp.json["@context"])
            if isinstance(value, dict)
        }
        assert "rism:hasItem" not in ids
        assert "rism:MaterialGroup" not in ids


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

    works_node = next(graph.objects(subject, rism.works))
    work_references_node = next(graph.objects(works_node, rism.workReferences))
    assert any(graph.objects(work_references_node, rism.hasWorkNode))


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
def test_work_context_expands_semantic_sections(client):
    _, ctx_resp = client.get("/api/v1/work.json")
    assert_json_contract(ctx_resp, status=200, required_keys=["@context"])
    work_context = ctx_resp.json["@context"]

    work_doc = {
        "@context": work_context,
        "id": "https://rism.online/works/49509",
        "type": "rism:Work",
        "label": {"en": ["Demetrio, WotG 1A.2"]},
        "creator": {
            "role": {
                "label": {"en": ["Composer/Author"]},
                "value": "cre",
                "id": "http://id.loc.gov/vocabulary/relators/cre",
            },
            "relatedTo": {
                "id": "https://rism.online/people/67338",
                "label": {"none": ["Gluck, Christoph Willibald (1714-1787)"]},
                "type": "rism:Person",
            },
        },
        "summary": [
            {
                "label": {"en": ["Text incipit"]},
                "value": {"none": ["Se fecondo e vigoroso crescer vede un arboscello"]},
            }
        ],
        "recordHistory": {
            "type": "rism:RecordHistory",
            "created": {"label": {"en": ["Created on"]}, "value": "2025-04-15T11:39:17Z"},
            "updated": {
                "label": {"en": ["Last modification"]},
                "value": "2026-03-16T09:38:14Z",
            },
        },
        "partOf": {
            "label": {"en": ["Item part of"]},
            "type": "rism:PartOfSection",
            "items": [
                {
                    "relationshipType": "rism:PrimaryPartOf",
                    "relatedTo": {
                        "id": "https://rism.online/publications/121",
                        "label": {"none": ["Catalogue"]},
                        "type": "rism:Publication",
                    },
                    "workNumber": "WotG 1A.2",
                }
            ],
        },
        "sources": {
            "sectionLabel": {"en": ["Sources"]},
            "url": "https://rism.online/works/49509/sources",
            "totalItems": 18,
        },
        "formOfWork": {
            "sectionLabel": {"en": ["Form of work"]},
            "items": [
                {
                    "id": "https://rism.online/subjects/25160",
                    "type": "rism:Subject",
                    "label": {"none": ["Operas"]},
                    "value": "Operas",
                }
            ],
        },
        "referencesNotes": {
            "sectionLabel": {"en": ["References and notes"]},
            "type": "rism:ReferencesNotesSection",
            "notes": [
                {
                    "label": {"en": ["Catalog of works"]},
                    "value": {"none": ["Reference text"]},
                }
            ],
        },
        "incipits": {
            "items": [
                {
                    "label": {"en": ["Incipit"]},
                    "rendered": [{"format": "image/svg+xml", "data": "<svg/>"}],
                    "notation": "4CDEF",
                }
            ]
        },
    }

    graph = Graph()
    graph.parse(data=json.dumps(work_doc), format="json-ld")

    subject = URIRef("https://rism.online/works/49509")
    rism = Namespace("https://rism.online/api/v1#")

    predicates = {str(pred) for pred in graph.predicates()}
    assert len(predicates) > 10
    assert (subject, RDF.type, rism.Work) in graph
    assert sum(1 for _ in graph.objects(subject, RDFS.label)) == 1
    assert any(graph.objects(subject, rism.recordHistory))
    assert any(graph.objects(subject, rism.sources))
    assert any(graph.objects(subject, rism.formOfWork))
    assert any(graph.objects(subject, rism.referencesNotes))
    assert any(graph.objects(subject, rism.hasSummary))
    assert not any(graph.subject_objects(rism.rendered))

    form_of_work_node = next(graph.objects(subject, rism.formOfWork))
    assert any(graph.objects(form_of_work_node, rism.hasFormOfWork))


@pytest.mark.endpoint
@pytest.mark.contract
def test_source_context_expands_semantic_sections(client):
    _, ctx_resp = client.get("/api/v1/source.json")
    assert_json_contract(ctx_resp, status=200, required_keys=["@context"])
    source_context = ctx_resp.json["@context"]

    source_doc = {
        "@context": source_context,
        "id": "https://rism.online/sources/117580",
        "type": "rism:Source",
        "typeLabel": {"en": ["Source"]},
        "label": {"en": ["16 Keyboard pieces; Manuscript copy; US-U x786.4108/M319"]},
        "sourceTypes": {
            "recordType": {"label": {"en": ["Collection"]}, "type": "rism:CollectionRecord"},
            "sourceType": {"label": {"en": ["Manuscript"]}, "type": "rism:ManuscriptSource"},
            "contentTypes": [
                {"label": {"en": ["Notated music"]}, "type": "rism:MusicalContent"}
            ],
        },
        "recordHistory": {
            "type": "rism:RecordHistory",
            "created": {"label": {"en": ["Created on"]}, "value": "2013-01-29T00:00:00Z"},
            "updated": {
                "label": {"en": ["Last modification"]},
                "value": "2025-08-13T20:20:04Z",
            },
        },
        "contents": {
            "sectionLabel": {"en": ["Title and content description"]},
            "summary": [
                {
                    "label": {"en": ["Standardized title"]},
                    "value": {"none": ["16 Keyboard pieces"]},
                    "type": ["dcterms:title", "rism:StandardizedTitle"],
                }
            ],
            "subjects": {
                "sectionLabel": {"en": ["Subject headings"]},
                "items": [
                    {
                        "id": "https://rism.online/subjects/25234",
                        "type": "rism:Subject",
                        "label": {"none": ["Anthems"]},
                        "value": "Anthems",
                    }
                ],
            },
        },
        "materialGroups": {
            "sectionLabel": {"en": ["Material description"]},
            "items": [
                {
                    "id": "https://rism.online/sources/117580/material-groups/01",
                    "type": "rism:MaterialGroup",
                    "label": {"none": ["Group 01"]},
                    "summary": [{"label": {"en": ["Date"]}, "value": {"none": ["1700 (1700c)"]}}],
                }
            ],
        },
        "relationships": {
            "sectionLabel": {"en": ["Relations"]},
            "items": [
                {
                    "role": {
                        "label": {"en": ["Former owner"]},
                        "value": "fmo",
                        "id": "http://id.loc.gov/vocabulary/relators/fmo",
                    },
                    "relatedTo": {
                        "id": "https://rism.online/people/30031975",
                        "label": {"none": ["Woodcock, Deborah"]},
                        "type": "rism:Person",
                    },
                }
            ],
        },
        "referencesNotes": {
            "sectionLabel": {"en": ["References and notes"]},
            "type": "rism:ReferencesNotesSection",
            "notes": [
                {
                    "label": {"en": ["General note"]},
                    "value": {"none": ["Manuscript of English provenance"]},
                }
            ],
        },
        "exemplars": {
            "id": "https://rism.online/sources/117580/holdings",
            "type": "rism:ExemplarsSection",
            "sectionLabel": {"en": ["Exemplars"]},
            "items": [
                {
                    "id": "https://rism.online/sources/117580/holdings/30000011",
                    "type": "rism:Holding",
                    "holdingType": "rism:ManuscriptHolding",
                    "sectionLabel": {"en": ["Exemplar"]},
                    "label": {"none": ["Example Holding"]},
                    "heldBy": {
                        "id": "https://rism.online/institutions/30000011",
                        "type": "rism:Institution",
                        "label": {"none": ["Example Institution"]},
                    },
                }
            ],
        },
        "sourceItems": {
            "sectionLabel": {"en": ["Items in this source"]},
            "url": "https://rism.online/sources/117580/contents",
            "totalItems": 2,
            "items": [
                {
                    "id": "https://rism.online/sources/117581",
                    "type": "rism:Source",
                    "typeLabel": {"en": ["Source"]},
                    "label": {"none": ["Nested item"]},
                    "sourceTypes": {
                        "recordType": {
                            "label": {"en": ["Single item"]},
                            "type": "rism:SingleItemRecord",
                        }
                    },
                    "recordHistory": {
                        "type": "rism:RecordHistory",
                        "created": {
                            "label": {"en": ["Created on"]},
                            "value": "2014-01-01T00:00:00Z",
                        },
                    },
                }
            ],
        },
        "externalResources": {
            "sectionLabel": {"en": ["Related resources"]},
            "items": [
                {
                    "type": "rism:ExternalResource",
                    "url": "https://example.org/iiif/manifest",
                    "label": {"none": ["IIIF manifest"]},
                    "resourceType": "rism:IIIFManifestLink",
                }
            ],
        },
        "dates": {
            "earliestDate": 1700,
            "latestDate": 1700,
            "dateStatement": "1700 (1700c)",
        },
        "properties": {
            "physicalDimensions": ["20 x 26 cm"],
        },
    }

    graph = Graph()
    graph.parse(data=json.dumps(source_doc), format="json-ld")

    subject = URIRef("https://rism.online/sources/117580")
    rism = Namespace("https://rism.online/api/v1#")
    dcterms = Namespace("http://purl.org/dc/terms/")
    schemaorg = Namespace("https://schema.org/")

    predicates = {str(pred) for pred in graph.predicates()}
    assert len(predicates) > 10
    assert (subject, RDF.type, rism.Source) in graph
    assert any(graph.objects(subject, rism.recordHistory))
    assert any(graph.objects(subject, rism.sourceTypes))
    assert any(graph.objects(subject, rism.materialGroups))
    assert any(graph.objects(subject, rism.hasRelationship))
    assert any(graph.objects(subject, rism.referencesNotes))
    assert any(graph.objects(subject, rism.holdings))
    assert any(graph.objects(subject, rism.sourceItems))
    assert any(graph.objects(subject, rism.externalResources))
    assert any(graph.objects(subject, rism.hasSummary))
    assert any(graph.objects(subject, rism.subjects))
    assert not any(graph.objects(subject, rism.contents))

    material_groups_node = next(graph.objects(subject, rism.materialGroups))
    material_group_node = next(graph.objects(material_groups_node, rism.hasMaterialGroup))
    assert (material_group_node, RDF.type, rism.MaterialGroup) in graph

    holdings_node = next(graph.objects(subject, rism.holdings))
    assert any(graph.objects(holdings_node, rism.hasHolding))

    subjects_node = next(graph.objects(subject, rism.subjects))
    assert any(graph.objects(subjects_node, rism.hasSubject))

    external_resources_node = next(graph.objects(subject, rism.externalResources))
    assert any(graph.objects(external_resources_node, rism.hasExternalResource))

    history_node = next(graph.objects(subject, rism.recordHistory))
    created_node = next(graph.objects(history_node, dcterms.created))
    updated_node = next(graph.objects(history_node, dcterms.modified))
    created_value = next(graph.objects(created_node, RDF.value))
    updated_value = next(graph.objects(updated_node, RDF.value))
    assert created_value.datatype == XSD.dateTime
    assert updated_value.datatype == XSD.dateTime

    source_items_node = next(graph.objects(subject, rism.sourceItems))
    assert any(graph.objects(source_items_node, rism.hasSourceItem))
    source_items_url = next(graph.objects(source_items_node, schemaorg.url))
    assert source_items_url.datatype == XSD.anyURI
    source_items_count = next(graph.objects(source_items_node, rism.totalItems))
    assert source_items_count.datatype == XSD.integer


@pytest.mark.endpoint
@pytest.mark.contract
def test_publication_context_expands_semantic_sections(client):
    _, ctx_resp = client.get("/api/v1/publication.json")
    assert_json_contract(ctx_resp, status=200, required_keys=["@context"])
    publication_context = ctx_resp.json["@context"]

    publication_doc = {
        "@context": publication_context,
        "id": "https://rism.online/publications/50007683",
        "type": "rism:Publication",
        "typeLabel": {"en": ["Work catalog"]},
        "label": {"none": ["KV 2024"]},
        "creator": {
            "role": {"label": {"en": ["Author"]}, "value": "aut", "id": "relators:aut"},
            "relatedTo": {
                "id": "https://rism.online/people/27690",
                "label": {"none": ["Köchel, Ludwig von (1800-1877)"]},
                "type": "rism:Person",
            },
        },
        "composer": {
            "id": "https://rism.online/people/115324",
            "label": {"none": ["Mozart, Wolfgang Amadeus (1756-1791)"]},
            "type": "rism:Person",
        },
        "properties": {
            "shortTitle": {"none": ["KV 2024"]},
            "publicationDates": {"none": ["2024"]},
        },
        "status": {
            "label": {"en": ["Partially completed"]},
            "value": "partial",
        },
        "recordHistory": {
            "type": "rism:RecordHistory",
            "created": {"label": {"en": ["Created on"]}, "value": "2024-04-02T14:59:15Z"},
            "updated": {
                "label": {"en": ["Last modification"]},
                "value": "2025-06-20T10:13:55Z",
            },
        },
        "summary": [
            {"label": {"en": ["Short title"]}, "value": {"none": ["KV 2024"]}},
            {"label": {"en": ["Date"]}, "value": {"none": ["2024"]}},
        ],
        "relationships": {
            "sectionLabel": {"en": ["Relations"]},
            "items": [
                {
                    "role": {
                        "label": {"en": ["Composer cross-reference"]},
                        "value": "att",
                        "id": "relators:att",
                    },
                    "relatedTo": {
                        "id": "https://rism.online/people/115324",
                        "label": {"none": ["Mozart, Wolfgang Amadeus (1756-1791)"]},
                        "type": "rism:Person",
                    },
                }
            ],
        },
        "notes": {
            "label": {"en": ["References and notes"]},
            "type": "rism:NotesSection",
            "notes": [
                {
                    "label": {"en": ["General note"]},
                    "value": {"none": ["Vorwort in Deutsch und Englisch"]},
                }
            ],
        },
        "works": {
            "sectionLabel": {"none": ["Works in this publication"]},
            "url": "https://rism.online/publications/50007683/works",
            "totalItems": 816,
        },
        "externalResources": {
            "sectionLabel": {"en": ["Related resources"]},
            "items": [
                {
                    "type": "rism:ExternalResource",
                    "url": "https://example.org/resource",
                    "label": {"none": ["Digitized"]},
                    "resourceType": "rism:DigitizationLink",
                }
            ],
        },
    }

    graph = Graph()
    graph.parse(data=json.dumps(publication_doc), format="json-ld")

    subject = URIRef("https://rism.online/publications/50007683")
    rism = Namespace("https://rism.online/api/v1#")
    dcterms = Namespace("http://purl.org/dc/terms/")
    schemaorg = Namespace("https://schema.org/")

    predicates = {str(pred) for pred in graph.predicates()}
    assert len(predicates) > 10
    assert (subject, RDF.type, rism.Publication) in graph
    assert any(graph.objects(subject, dcterms.creator))
    assert any(graph.objects(subject, rism.composer))
    assert any(graph.objects(subject, rism.shortTitle))
    assert any(graph.objects(subject, rism.publicationDates))
    assert any(graph.objects(subject, rism.status))
    assert any(graph.objects(subject, rism.recordHistory))
    assert any(graph.objects(subject, rism.hasSummary))
    assert any(graph.objects(subject, rism.hasRelationship))
    assert any(graph.objects(subject, rism.notes))
    assert any(graph.objects(subject, rism.works))
    assert any(graph.objects(subject, rism.externalResources))

    external_resources_node = next(graph.objects(subject, rism.externalResources))
    assert any(graph.objects(external_resources_node, rism.hasExternalResource))

    works_node = next(graph.objects(subject, rism.works))
    works_url = next(graph.objects(works_node, schemaorg.url))
    assert works_url.datatype == XSD.anyURI
    works_count = next(graph.objects(works_node, rism.totalItems))
    assert works_count.datatype == XSD.integer


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
