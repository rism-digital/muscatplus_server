# ruff: noqa: S101

from __future__ import annotations

import json

import pytest
from pyoxigraph import NamedNode, RdfFormat, parse
from sanic import response

from search_server.helpers.linked_data import to_ntriples
from tests.conftest import assert_content_type, assert_json_contract


class Namespace:
    def __init__(self, base: str) -> None:
        self.base = base

    def __getattr__(self, name: str) -> NamedNode:
        return NamedNode(f"{self.base}{name}")


class _RDF:
    type = NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    value = NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#value")


class _RDFS:
    label = NamedNode("http://www.w3.org/2000/01/rdf-schema#label")


class _XSD:
    dateTime = NamedNode("http://www.w3.org/2001/XMLSchema#dateTime")
    anyURI = NamedNode("http://www.w3.org/2001/XMLSchema#anyURI")
    integer = NamedNode("http://www.w3.org/2001/XMLSchema#integer")


RDF = _RDF()
RDFS = _RDFS()
XSD = _XSD()
URIRef = NamedNode


class Graph:
    def __init__(self) -> None:
        self.quads = set()

    def parse(self, data: str, format: str):
        rdf_format = RdfFormat.JSON_LD if format == "json-ld" else RdfFormat.N_TRIPLES
        self.quads = set(
            parse(
                input=data.encode("utf-8"),
                format=rdf_format,
                without_named_graphs=True,
                lenient=True,
            )
        )
        return self

    def predicates(self):
        return (quad.predicate for quad in self.quads)

    def objects(self, subject, predicate):
        return (
            quad.object
            for quad in self.quads
            if quad.subject == subject and quad.predicate == predicate
        )

    def subject_objects(self, predicate):
        return (
            (quad.subject, quad.object)
            for quad in self.quads
            if quad.predicate == predicate
        )

    def __contains__(self, triple) -> bool:
        subject, predicate, obj = triple
        return any(
            quad.subject == subject
            and quad.predicate == predicate
            and quad.object == obj
            for quad in self.quads
        )


@pytest.mark.endpoint
@pytest.mark.contract
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/source.json",
        "/api/v1/person.json",
        "/api/v1/institution.json",
        "/api/v1/place.json",
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
        "/api/v1/place.json",
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

        item_aliases = [
            value.get("items")
            for value in iter_context_values(resp.json["@context"])
            if isinstance(value, dict) and "items" in value
        ]
        assert "@set" not in item_aliases


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
            "id": "https://rism.online/people/115324/relationships",
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
        "externalAuthorities": {
            "id": "https://rism.online/people/115324/external-authorities",
            "label": {"en": ["Other standard identifier"]},
            "type": "rism:ExternalAuthoritiesSection",
            "items": [
                {
                    "id": "https://rism.online/people/115324/external-authorities/viaf32197206",
                    "type": "rism:ExternalAuthority",
                    "url": "https://viaf.org/viaf/32197206",
                    "base": "https://viaf.org/viaf/",
                    "label": {"none": ["Virtual Internet Authority File (VIAF): 32197206"]},
                    "value": {"none": ["32197206"]},
                }
            ],
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
        "properties": {
            "authorityLinks": [
                {
                    "id": "https://rism.online/people/115324/external-authorities/viaf32197206",
                    "scheme": "viaf",
                    "identifier": "32197206",
                    "uri": "https://viaf.org/viaf/32197206",
                },
                {
                    "id": "https://rism.online/people/115324/external-authorities/iccuCFIV019276",
                    "scheme": "iccu",
                    "identifier": "CFIV019276",
                },
            ],
            "sameAs": [
                "https://viaf.org/viaf/32197206",
            ],
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
    schemaorg = Namespace("https://schema.org/")

    predicates = {str(pred) for pred in graph.predicates()}
    assert len(predicates) > 6
    assert (subject, RDF.type, rism.Person) in graph
    assert sum(1 for _ in graph.objects(subject, RDFS.label)) == 1

    # Verify explicit mapping for record history and relationships.
    assert any(graph.objects(subject, rism.recordHistory))
    relationship_section = next(graph.objects(subject, rism.relationships))
    assert isinstance(relationship_section, URIRef)
    relationship_nodes = list(graph.objects(relationship_section, rism.hasRelationship))
    assert relationship_nodes
    assert any(graph.objects(relationship_nodes[0], rism.hasRole))
    assert any(graph.objects(relationship_nodes[0], dcterms.relation))

    works_node = next(graph.objects(subject, rism.works))
    work_references_node = next(graph.objects(works_node, rism.workReferences))
    assert any(graph.objects(work_references_node, rism.hasWorkNode))
    assert any(graph.objects(subject, schemaorg.sameAs))

    external_authorities_section = next(graph.objects(subject, rism.externalAuthorities))
    assert isinstance(external_authorities_section, URIRef)
    external_authorities_items = list(
        graph.objects(external_authorities_section, rism.hasExternalAuthority)
    )
    assert len(external_authorities_items) == 1
    assert isinstance(external_authorities_items[0], URIRef)

    authority_nodes = list(graph.objects(subject, rism.hasExternalAuthority))
    assert len(authority_nodes) == 2
    assert all(isinstance(node, URIRef) for node in authority_nodes)
    authority_scheme_values = {
        next(graph.objects(authority_node, rism.authorityScheme)).value
        for authority_node in authority_nodes
        if any(graph.objects(authority_node, rism.authorityScheme))
    }
    assert authority_scheme_values == {"viaf", "iccu"}
    assert any(graph.objects(subject, schemaorg.sameAs))


@pytest.mark.endpoint
@pytest.mark.contract
def test_to_ntriples_materializes_direct_relationship_triples(client):
    _, ctx_resp = client.get("/api/v1/person.json")
    assert_json_contract(ctx_resp, status=200, required_keys=["@context"])
    person_context = ctx_resp.json["@context"]

    person_doc = {
        "@context": person_context,
        "id": "https://rism.online/people/115324",
        "type": "rism:Person",
        "label": {"none": ["Mozart, Wolfgang Amadeus (1756-1791)"]},
        "relationships": {
            "id": "https://rism.online/people/115324/relationships",
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
            ],
        },
    }

    graph = Graph()
    graph.parse(to_ntriples(person_doc), format="n-triples")

    subject = URIRef("https://rism.online/people/115324")
    section = URIRef("https://rism.online/people/115324/relationships")
    related_person = URIRef("https://rism.online/people/276624")
    role = URIRef("https://rism.online/vocabulary/relationship/father_of")
    rism = Namespace("https://rism.online/api/v1#")
    dcterms = Namespace("http://purl.org/dc/terms/")

    assert (subject, rism.relationships, section) in graph
    relationship_nodes = list(graph.objects(section, rism.hasRelationship))
    assert relationship_nodes
    assert any(graph.objects(relationship_nodes[0], rism.hasRole))
    assert any(graph.objects(relationship_nodes[0], dcterms.relation))
    assert (subject, role, related_person) in graph


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
            "addresses": [
                {
                    "street": {
                        "label": {"en": ["Street address"]},
                        "value": {"none": ["Schlossstrasse 1"]},
                    },
                    "city": {
                        "label": {"en": ["City"]},
                        "value": {"none": ["Dresden"]},
                    },
                    "postcode": {
                        "label": {"en": ["Postal code"]},
                        "value": {"none": ["01067"]},
                    },
                    "country": {
                        "label": {"en": ["Country"]},
                        "value": {"none": ["Germany"]},
                    },
                    "county": {
                        "label": {"en": ["County / province"]},
                        "value": {"none": ["Saxony"]},
                    },
                    "note": {
                        "label": {"en": ["Public note"]},
                        "value": {"none": ["Main entrance on west side"]},
                    },
                }
            ],
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
            "authorityLinks": [
                {
                    "id": "https://rism.online/institutions/30000042/external-authorities/dnb123456-7",
                    "scheme": "dnb",
                    "identifier": "123456-7",
                    "uri": "https://d-nb.info/gnd/123456-7",
                },
                {
                    "id": "https://rism.online/institutions/30000042/external-authorities/isilDE-588",
                    "scheme": "isil",
                    "identifier": "DE-588",
                },
            ],
            "sameAs": [
                "https://d-nb.info/gnd/123456-7",
            ],
        },
    }

    graph = Graph()
    graph.parse(data=json.dumps(institution_doc), format="json-ld")

    subject = URIRef("https://rism.online/institutions/30000042")
    rism = Namespace("https://rism.online/api/v1#")
    dcterms = Namespace("http://purl.org/dc/terms/")
    schemaorg = Namespace("https://schema.org/")

    predicates = {str(pred) for pred in graph.predicates()}
    assert len(predicates) > 10
    assert (subject, RDF.type, rism.Institution) in graph
    assert sum(1 for _ in graph.objects(subject, RDFS.label)) == 1
    assert any(graph.objects(subject, rism.organizationDetails))
    assert any(graph.objects(subject, rism.recordHistory))
    assert any(graph.objects(subject, rism.hasLocation))
    assert any(graph.objects(subject, rism.sources))
    assert any(graph.objects(subject, schemaorg.sameAs))

    location_node = next(graph.objects(subject, rism.hasLocation))
    address_nodes = list(graph.objects(location_node, schemaorg.address))
    assert address_nodes
    assert any(graph.objects(address_nodes[0], schemaorg.streetAddress))
    assert any(graph.objects(address_nodes[0], schemaorg.addressLocality))
    assert any(graph.objects(address_nodes[0], schemaorg.postalCode))
    assert any(graph.objects(address_nodes[0], schemaorg.addressCountry))
    assert any(graph.objects(address_nodes[0], schemaorg.addressRegion))
    assert any(graph.objects(address_nodes[0], schemaorg.description))

    relationship_section = next(graph.objects(subject, rism.relationships))
    relationship_nodes = list(graph.objects(relationship_section, rism.hasRelationship))
    assert relationship_nodes
    assert any(graph.objects(relationship_nodes[0], rism.hasRole))
    assert any(graph.objects(relationship_nodes[0], dcterms.relation))

    authority_nodes = list(graph.objects(subject, rism.hasExternalAuthority))
    assert len(authority_nodes) == 2
    authority_scheme_values = {
        next(graph.objects(authority_node, rism.authorityScheme)).value
        for authority_node in authority_nodes
        if any(graph.objects(authority_node, rism.authorityScheme))
    }
    assert authority_scheme_values == {"dnb", "isil"}
    authority_identifier_values = {
        next(graph.objects(authority_node, RDF.value)).value
        for authority_node in authority_nodes
        if any(graph.objects(authority_node, RDF.value))
    }
    assert authority_identifier_values == {"123456-7", "DE-588"}
    authority_urls = [
        obj
        for authority_node in authority_nodes
        for obj in graph.objects(authority_node, rism.authorityUrl)
    ]
    assert len(authority_urls) == 1


@pytest.mark.endpoint
@pytest.mark.contract
def test_place_context_expands_semantic_sections(client):
    _, ctx_resp = client.get("/api/v1/place.json")
    assert_json_contract(ctx_resp, status=200, required_keys=["@context"])
    place_context = ctx_resp.json["@context"]

    place_doc = {
        "@context": place_context,
        "id": "https://rism.online/places/30000655",
        "type": "rism:Place",
        "typeLabel": {"en": ["Place"]},
        "label": {"none": ["Berlin"]},
        "summary": [
            {
                "label": {"en": ["Country"]},
                "value": {"none": ["Germany"]},
            }
        ],
        "externalAuthorities": {
            "id": "https://rism.online/places/30000655/external-authorities",
            "label": {"en": ["Other standard identifier"]},
            "type": "rism:ExternalAuthoritiesSection",
            "items": [
                {
                    "id": "https://rism.online/places/30000655/external-authorities/wkpQ64",
                    "type": "rism:ExternalAuthority",
                    "url": "https://www.wikidata.org/wiki/Q64",
                    "base": "https://www.wikidata.org/wiki/",
                    "label": {"none": ["Wikidata: Q64"]},
                    "value": {"none": ["Q64"]},
                }
            ],
        },
        "sources": {
            "type": "rism:PlaceSourceList",
            "items": [
                {
                    "id": "https://rism.online/sources/117580",
                    "type": "rism:Source",
                    "label": {"none": ["Example Source"]},
                }
            ],
        },
        "people": {
            "type": "rism:PlacePersonList",
            "items": [
                {
                    "id": "https://rism.online/people/115324",
                    "type": "rism:Person",
                    "label": {"none": ["Mozart, Wolfgang Amadeus (1756-1791)"]},
                }
            ],
        },
        "institutions": {
            "type": "rism:PlaceInstitutionList",
            "items": [
                {
                    "id": "https://rism.online/institutions/30000655",
                    "type": "rism:Institution",
                    "label": {"none": ["Staatsbibliothek zu Berlin - Preußischer Kulturbesitz"]},
                }
            ],
        },
        "properties": {
            "authorityLinks": [
                {
                    "id": "https://rism.online/places/30000655/external-authorities/wkpQ64",
                    "scheme": "wkp",
                    "identifier": "Q64",
                    "uri": "https://www.wikidata.org/wiki/Q64",
                },
                {
                    "id": "https://rism.online/places/30000655/external-authorities/isilDE-1",
                    "scheme": "isil",
                    "identifier": "DE-1",
                },
            ],
            "sameAs": [
                "https://www.wikidata.org/wiki/Q64",
            ],
        },
    }

    graph = Graph()
    graph.parse(data=json.dumps(place_doc), format="json-ld")

    subject = URIRef("https://rism.online/places/30000655")
    rism = Namespace("https://rism.online/api/v1#")
    schemaorg = Namespace("https://schema.org/")

    predicates = {str(pred) for pred in graph.predicates()}
    assert len(predicates) > 5
    assert (subject, RDF.type, rism.Place) in graph
    assert sum(1 for _ in graph.objects(subject, RDFS.label)) == 1
    assert any(graph.objects(subject, rism.hasSummary))
    assert not any(graph.objects(subject, rism.sources))
    assert not any(graph.objects(subject, rism.people))
    assert not any(graph.objects(subject, rism.institutions))
    assert any(graph.objects(subject, rism.externalAuthorities))
    assert any(graph.objects(subject, schemaorg.sameAs))

    authority_nodes = list(graph.objects(subject, rism.hasExternalAuthority))
    assert len(authority_nodes) == 2
    authority_scheme_values = {
        next(graph.objects(authority_node, rism.authorityScheme)).value
        for authority_node in authority_nodes
        if any(graph.objects(authority_node, rism.authorityScheme))
    }
    assert authority_scheme_values == {"wkp", "isil"}


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
            "id": "https://rism.online/works/49509/references-notes",
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
    references_notes_node = next(graph.objects(subject, rism.referencesNotes))
    assert isinstance(references_notes_node, URIRef)
    assert any(graph.objects(subject, rism.hasSummary))
    part_of_section = next(graph.objects(subject, rism.partOf))
    assert any(graph.objects(part_of_section, rism.isPartOf))
    incipits_section = next(graph.objects(subject, rism.incipits))
    assert any(graph.objects(incipits_section, rism.hasIncipit))
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
            "id": "https://rism.online/sources/117580/relationships",
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
            "id": "https://rism.online/sources/117580/references-notes",
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
    relationship_section = next(graph.objects(subject, rism.relationships))
    assert isinstance(relationship_section, URIRef)
    assert any(graph.objects(relationship_section, rism.hasRelationship))
    assert any(graph.objects(subject, rism.referencesNotes))
    references_notes_node = next(graph.objects(subject, rism.referencesNotes))
    assert isinstance(references_notes_node, URIRef)
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
            "id": "https://rism.online/publications/50007683/relationships",
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
            "id": "https://rism.online/publications/50007683/notes",
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
    relationship_section = next(graph.objects(subject, rism.relationships))
    assert isinstance(relationship_section, URIRef)
    assert any(graph.objects(relationship_section, rism.hasRelationship))
    assert any(graph.objects(subject, rism.notes))
    notes_node = next(graph.objects(subject, rism.notes))
    assert isinstance(notes_node, URIRef)
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
