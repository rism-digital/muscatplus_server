from __future__ import annotations

import argparse
import logging
import logging.config
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypedDict

import yaml
from pyoxigraph import DefaultGraph, Literal, NamedNode, Quad, RdfFormat, serialize
from pyprttl import PrttlError, format_turtle

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(PROJECT_ROOT))

from search_server.helpers.identifiers import RISM_RELATIONSHIP_BASE  # noqa: E402
from search_server.helpers.jsonld import (  # noqa: E402
    RISM_JSONLD_INSTITUTION_CONTEXT,
    RISM_JSONLD_PERSON_CONTEXT,
    RISM_JSONLD_PLACE_CONTEXT,
    RISM_JSONLD_PUBLICATION_CONTEXT,
    RISM_JSONLD_SOURCE_CONTEXT,
    RISM_JSONLD_WORK_CONTEXT,
)

PREFIXES = {
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "geojson": "https://purl.org/geojson/vocab#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "pmo": "http://performedmusicontology.org/ontology/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rdau": "http://rdaregistry.info/Elements/u/",
    "relators": "http://id.loc.gov/vocabulary/relators/",
    "rism": "https://rism.online/api/v1#",
    "rismrel": RISM_RELATIONSHIP_BASE,
    "schemaorg": "https://schema.org/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}

CONTEXTS = {
    "source": RISM_JSONLD_SOURCE_CONTEXT,
    "person": RISM_JSONLD_PERSON_CONTEXT,
    "institution": RISM_JSONLD_INSTITUTION_CONTEXT,
    "place": RISM_JSONLD_PLACE_CONTEXT,
    "work": RISM_JSONLD_WORK_CONTEXT,
    "publication": RISM_JSONLD_PUBLICATION_CONTEXT,
}


class OntologyMetadata(TypedDict):
    iri: str
    title: str
    description: str
    version: str
    see_also: list[str]
    comment: str


ONTOLOGY_METADATA: OntologyMetadata = {
    "iri": "rism:",
    "title": "RISM service ontology",
    "description": (
        "Descriptive ontology for the RDF emitted by the RISM service as of the "
        "current JSON-LD contexts and serializers. It is intentionally query-oriented "
        "and LLM-friendly: it documents classes, predicates, structural wrapper "
        "nodes, and common SPARQL paths rather than enforcing strict cardinalities."
    ),
    "version": "0.2.0",
    "see_also": ["https://rism.online/"],
    "comment": (
        "This file describes service RDF, not every JSON field in API responses. "
        "Some route-specific JSON structures are intentionally excluded from RDF by "
        "null-mapped context terms."
    ),
}

CLASS_METADATA = {
    "rism:Source": {
        "label": "Source",
        "comment": (
            "A source record. Sources can carry creator relationships, dates, summary "
            "values, source-type classification, material groups, holdings, incipits, "
            "subjects, references and notes, relationships, works, part-of links, and "
            "external resources."
        ),
        "query_patterns": [
            "?source a rism:Source .",
            "?source rism:holdings/rism:hasHolding ?holding . ?holding rism:hasHoldingInstitution ?institution .",
            "?source dcterms:creator ?creator . ?creator dcterms:relation ?person ; rism:hasRole relators:cre .",
            "?source rism:hasDates/rism:earliestDate ?year .",
            "MINUS { ?source rism:partOf/rism:isPartOf ?parent . }",
        ],
    },
    "rism:Person": {
        "label": "Person",
        "comment": "A person authority record. Person display labels usually use language tag 'none'.",
        "equivalent_classes": ["foaf:Person"],
        "query_patterns": [
            '?person a rism:Person ; rdfs:label ?name . FILTER(LANG(?name) = "none")'
        ],
    },
    "rism:Institution": {
        "label": "Institution",
        "comment": (
            "An institution authority record, including holding institutions, "
            "publishers, former owners, and other corporate agents."
        ),
        "equivalent_classes": ["schemaorg:Organization"],
        "query_patterns": [
            "?institution a rism:Institution ; rism:hasSiglum ?siglum .",
            "?institution rism:hasSiglum ?siglum ; rism:hasCountryCodes ?countryCode .",
            "?institution rism:hasLocation/schemaorg:address ?address .",
        ],
    },
    "rism:Place": {
        "label": "Place",
        "comment": (
            "A place record. In service RDF, place records currently expose their own "
            "summary and external-authority data, but embedded JSON lists of sources, "
            "people, and institutions are intentionally not mapped into RDF."
        ),
        "equivalent_classes": ["schemaorg:Place"],
        "query_patterns": ["?place a rism:Place ; rdfs:label ?name ."],
        "service_notes": [
            "The place API response contains additional JSON structures that are null-mapped in the place context and therefore do not contribute triples.",
            "Do not infer RDF paths from the JSON keys sources, people, or institutions on place responses; those keys are intentionally excluded from RDF.",
        ],
    },
    "rism:Work": {
        "label": "Work",
        "comment": (
            "A work record. Works can have creators, relationships, incipits, "
            "sources, form-of-work links, references and notes, external resources, "
            "and summary values."
        ),
        "query_patterns": [
            "?work a rism:Work .",
            "?work rism:formOfWork/rism:hasFormOfWork ?subject .",
            "?work rism:incipits/rism:hasIncipit ?incipit .",
        ],
    },
    "rism:Publication": {
        "label": "Publication",
        "comment": "A bibliographic publication or reference record.",
        "query_patterns": ["?publication a rism:Publication ."],
    },
    "rism:Subject": {
        "label": "Subject heading",
        "comment": "A subject heading record used by sources and works.",
        "query_patterns": [
            "?subject a rism:Subject ; rdf:value ?term .",
            "?source rism:subjects/rism:hasSubject ?subject .",
            "?work rism:formOfWork/rism:hasFormOfWork ?subject .",
        ],
    },
    "rism:Holding": {
        "label": "Holding",
        "comment": (
            "A holding or exemplar for a source, usually linked to a holding "
            "institution and carrying copy-specific summaries, notes, and a holding type."
        ),
        "query_patterns": [
            "?source rism:holdings/rism:hasHolding ?holding . ?holding rism:hasHoldingInstitution ?institution ."
        ],
    },
    "rism:Incipit": {
        "label": "Incipit",
        "comment": (
            "A musical incipit with Plaine and Easie clef, key signature, time "
            "signature, notation data, optional encodings, and summary values."
        ),
        "query_patterns": [
            "?source rism:incipits/rism:hasIncipit ?incipit . ?incipit rism:hasPAEData ?pae ."
        ],
    },
    "rism:MaterialGroup": {
        "label": "Material group",
        "comment": (
            "A material-description node within a source. Material groups can carry "
            "summaries, notes, relationships, and external resources."
        ),
        "query_patterns": [
            "?source rism:materialGroups/rism:hasMaterialGroup ?materialGroup ."
        ],
    },
    "rism:ExternalResource": {"label": "External resource"},
    "rism:ExternalRecord": {"label": "External record"},
    "rism:ExternalAuthority": {"label": "External authority"},
    "rism:DigitalObject": {"label": "Digital object"},
    "rism:InventoryItem": {"label": "Inventory item"},
    "rism:RecordHistory": {
        "label": "Record history",
        "comment": "Creation and modification metadata for a record.",
    },
    "rism:Section": {
        "label": "Section",
        "comment": "A structural node used by the service to group repeated or sectioned data.",
    },
    "rism:ExemplarsSection": {
        "label": "Exemplars section",
        "subclass_of": ["rism:Section"],
    },
    "rism:IncipitsSection": {
        "label": "Incipits section",
        "subclass_of": ["rism:Section"],
    },
    "rism:PartOfSection": {"label": "Part-of section", "subclass_of": ["rism:Section"]},
    "rism:ReferencesNotesSection": {
        "label": "References and notes section",
        "subclass_of": ["rism:Section"],
    },
    "rism:ExternalResourcesSection": {
        "label": "External resources section",
        "subclass_of": ["rism:Section"],
    },
    "rism:ExternalAuthoritiesSection": {
        "label": "External authorities section",
        "subclass_of": ["rism:Section"],
    },
    "rism:DigitalObjectsSection": {
        "label": "Digital objects section",
        "subclass_of": ["rism:Section"],
    },
    "rism:LocationAddressSection": {
        "label": "Location and address section",
        "subclass_of": ["rism:Section"],
    },
    "rism:NotesSection": {"label": "Notes section", "subclass_of": ["rism:Section"]},
    "rism:WorksSection": {"label": "Works section", "subclass_of": ["rism:Section"]},
    "rism:VariantNamesSection": {
        "label": "Variant names section",
        "subclass_of": ["rism:Section"],
    },
    "rism:ExternalWorkReferencesSection": {
        "label": "External work references section",
        "subclass_of": ["rism:Section"],
    },
    "rism:WorksCatalogsSection": {
        "label": "Works catalogs section",
        "subclass_of": ["rism:Section"],
    },
    "rism:SourceType": {"label": "Source type"},
    "rism:PrintedSource": {
        "label": "Printed source",
        "subclass_of": ["rism:SourceType"],
        "query_patterns": [
            "?source rism:sourceTypes/rism:sourceType ?sourceType . ?sourceType a rism:PrintedSource ."
        ],
    },
    "rism:ManuscriptSource": {
        "label": "Manuscript source",
        "subclass_of": ["rism:SourceType"],
        "query_patterns": [
            "?source rism:sourceTypes/rism:sourceType ?sourceType . ?sourceType a rism:ManuscriptSource ."
        ],
    },
    "rism:RecordType": {"label": "Record type"},
    "rism:ItemRecord": {"label": "Item record", "subclass_of": ["rism:RecordType"]},
    "rism:SingleItemRecord": {
        "label": "Single item record",
        "subclass_of": ["rism:RecordType"],
    },
    "rism:CollectionRecord": {
        "label": "Collection record",
        "subclass_of": ["rism:RecordType"],
    },
    "rism:ContentType": {"label": "Content type"},
    "rism:MusicalContent": {
        "label": "Musical content",
        "subclass_of": ["rism:ContentType"],
    },
    "rism:MaterialType": {"label": "Material type"},
    "rism:AutographMaterial": {
        "label": "Autograph manuscript material",
        "subclass_of": ["rism:MaterialType"],
        "query_patterns": [
            "?source rism:sourceTypes/rism:materialTypes ?materialType . ?materialType a rism:AutographMaterial ."
        ],
    },
    "rism:HoldingType": {"label": "Holding type"},
    "rism:ManuscriptHolding": {
        "label": "Manuscript holding",
        "subclass_of": ["rism:HoldingType"],
    },
    "rism:PrintHolding": {
        "label": "Print holding",
        "subclass_of": ["rism:HoldingType"],
    },
    "rism:RelationshipQualifier": {"label": "Relationship qualifier"},
    "rism:PartOfRelationship": {"label": "Part-of relationship type"},
}

RELATIONSHIP_PROPERTY_METADATA = {
    # These role predicates are published as first-class ontology terms even
    # though service RDF still uses the existing n-ary rism:hasRole model.
    "rismrel:parent_of": {
        "property_type": "object",
        "label": "parent of",
        "comment": "Generic parent relation introduced to group father_of and mother_of.",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
        "subproperty_of": ["schemaorg:children"],
    },
    "rismrel:sibling_of": {
        "property_type": "object",
        "label": "sibling of",
        "comment": "Generic sibling relation introduced to group brother_of and sister_of.",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
        "equivalent_properties": ["schemaorg:sibling"],
    },
    "rismrel:brother_of": {
        "property_type": "object",
        "label": "brother of",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
        "subproperty_of": ["rismrel:sibling_of"],
    },
    "rismrel:child_of": {
        "property_type": "object",
        "label": "child of",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
        "subproperty_of": ["schemaorg:parent"],
    },
    "rismrel:confused_with": {
        "property_type": "object",
        "label": "confused with",
        "comment": "Editorial or bibliographic confusion relation, not an identity relation.",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
    },
    "rismrel:father_of": {
        "property_type": "object",
        "label": "father of",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
        "subproperty_of": ["rismrel:parent_of"],
        "inverse_of": ["rismrel:child_of"],
    },
    "rismrel:married_to": {
        "property_type": "object",
        "label": "married to",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
        "equivalent_properties": ["schemaorg:spouse"],
    },
    "rismrel:mother_of": {
        "property_type": "object",
        "label": "mother of",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
        "subproperty_of": ["rismrel:parent_of"],
        "inverse_of": ["rismrel:child_of"],
    },
    "rismrel:other": {
        "property_type": "object",
        "label": "other",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
    },
    "rismrel:related_to": {
        "property_type": "object",
        "label": "related to",
        "comment": "Broad local association, only approximately aligned to schemaorg:knows.",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
        "subproperty_of": ["schemaorg:knows"],
    },
    "rismrel:sister_of": {
        "property_type": "object",
        "label": "sister of",
        "domain": ["rism:Person"],
        "range": ["rism:Person"],
        "subproperty_of": ["rismrel:sibling_of"],
    },
    "rismrel:active_in": {
        "property_type": "object",
        "label": "active in",
        "comment": "Generic activity-location relation introduced to group country_active, place_active, and region_active.",
        "range": ["rism:Place"],
        "subproperty_of": ["schemaorg:workLocation"],
    },
    "rismrel:go": {
        "property_type": "object",
        "label": "place of birth",
        "range": ["rism:Place"],
        "equivalent_properties": ["schemaorg:birthPlace"],
    },
    "rismrel:ha": {
        "property_type": "object",
        "label": "place of origin",
        "comment": "Place of origin is kept local because its scope varies across records and is not safely exact to a single Schema.org property.",
        "range": ["rism:Place"],
    },
    "rismrel:so": {
        "property_type": "object",
        "label": "place of death",
        "range": ["rism:Place"],
        "equivalent_properties": ["schemaorg:deathPlace"],
    },
    "rismrel:wl": {
        "property_type": "object",
        "label": "country active",
        "range": ["rism:Place"],
        "subproperty_of": ["rismrel:active_in"],
    },
    "rismrel:wo": {
        "property_type": "object",
        "label": "place active",
        "range": ["rism:Place"],
        "subproperty_of": ["rismrel:active_in"],
    },
    "rismrel:wr": {
        "property_type": "object",
        "label": "region active",
        "range": ["rism:Place"],
        "subproperty_of": ["rismrel:active_in"],
    },
    "rismrel:xp": {
        "property_type": "object",
        "label": "related place",
        "comment": "Broad local association to a place, kept local because there is no safely exact external property.",
        "range": ["rism:Place"],
    },
}

BASE_PROPERTY_METADATA = {
    "rism:queryPattern": {
        "property_type": "annotation",
        "label": "query pattern",
        "comment": "A SPARQL path or idiom useful for prompt-to-SPARQL systems.",
    },
    "rism:serviceNote": {
        "property_type": "annotation",
        "label": "service note",
        "comment": "Implementation note about how the service emits RDF.",
        "service_notes": [
            "For route-specific record contexts, class labels are materialized onto the class IRIs through synthesized @included nodes. In service RDF, this means classes such as rism:Source, rism:Person, rism:Subject, rism:Holding, rism:PrintedSource, or rism:AutographMaterial can carry rdfs:label triples even when the instance JSON only contained type/typeLabel pairs."
        ],
    },
    "dcterms:creator": {
        "label": "creator node",
        "comment": (
            "Links a source, work, or publication to a creator relationship node. "
            "The node usually carries dcterms:relation, rism:hasRole, and optionally "
            "rism:hasQualifier."
        ),
        "query_patterns": [
            "?record dcterms:creator ?creator . ?creator dcterms:relation ?person ; rism:hasRole relators:cre ."
        ],
    },
    "rism:relationships": {
        "label": "relationships section",
        "comment": "Links a record or material group to a relationship section.",
        "query_patterns": [
            "?record rism:relationships/rism:hasRelationship ?relationship ."
        ],
    },
    "rism:hasRelationship": {
        "label": "has relationship",
        "comment": (
            "Links a relationship section to a relationship node. Relationship nodes "
            "usually use dcterms:relation for the related resource and rism:hasRole "
            "for the role."
        ),
        "query_patterns": [
            "?relationship dcterms:relation ?related ; rism:hasRole ?role ."
        ],
    },
    "rism:hasRole": {
        "label": "has role",
        "comment": "A role for creator and relationship nodes. Values commonly come from the Library of Congress relators vocabulary.",
    },
    "rism:hasQualifier": {
        "label": "has qualifier",
        "range": ["rism:RelationshipQualifier"],
    },
    "rism:holdings": {
        "label": "holdings section",
        "domain": ["rism:Source"],
        "range": ["rism:ExemplarsSection"],
        "query_patterns": ["?source rism:holdings/rism:hasHolding ?holding ."],
    },
    "rism:hasHolding": {
        "label": "has holding",
        "domain": ["rism:ExemplarsSection"],
        "range": ["rism:Holding"],
    },
    "rism:hasHoldingInstitution": {
        "label": "has holding institution",
        "domain": ["rism:Holding"],
        "range": ["rism:Institution"],
        "query_patterns": ["?holding rism:hasHoldingInstitution ?institution ."],
    },
    "rism:incipits": {
        "label": "incipits section",
        "range": ["rism:IncipitsSection"],
        "query_patterns": ["?record rism:incipits/rism:hasIncipit ?incipit ."],
    },
    "rism:hasIncipit": {
        "label": "has incipit",
        "domain": ["rism:IncipitsSection"],
        "range": ["rism:Incipit"],
    },
    "rism:materialGroups": {
        "label": "material groups section",
        "domain": ["rism:Source"],
        "range": ["rism:Section"],
        "query_patterns": [
            "?source rism:materialGroups/rism:hasMaterialGroup ?materialGroup ."
        ],
    },
    "rism:hasMaterialGroup": {
        "label": "has material group",
        "range": ["rism:MaterialGroup"],
    },
    "rism:partOf": {
        "label": "part-of section",
        "range": ["rism:PartOfSection"],
        "query_patterns": ["MINUS { ?source rism:partOf/rism:isPartOf ?parent . }"],
    },
    "rism:isPartOf": {
        "label": "is part of",
        "comment": "Links a part-of section to a part-of node that uses dcterms:relation for the parent resource.",
    },
    "rism:workCatalogRelationship": {
        "label": "work catalog relationship",
        "range": ["rism:PartOfRelationship"],
    },
    "rism:sourceTypes": {
        "label": "source types block",
        "domain": ["rism:Source"],
        "comment": "Links a source to a wrapper node grouping record type, source type, content types, and material types.",
    },
    "rism:recordType": {"label": "record type", "range": ["rism:RecordType"]},
    "rism:sourceType": {"label": "source type", "range": ["rism:SourceType"]},
    "rism:contentTypes": {"label": "content types", "range": ["rism:ContentType"]},
    "rism:materialTypes": {"label": "material types", "range": ["rism:MaterialType"]},
    "rism:subjects": {
        "label": "subjects section",
        "comment": "Links a source to a subjects wrapper node.",
        "query_patterns": ["?source rism:subjects/rism:hasSubject ?subject ."],
    },
    "rism:hasSubject": {"label": "has subject", "range": ["rism:Subject"]},
    "rism:formOfWork": {
        "label": "form of work section",
        "comment": "Links a work to a wrapper node whose entries are reached by rism:hasFormOfWork.",
    },
    "rism:hasFormOfWork": {"label": "has form of work", "range": ["rism:Subject"]},
    "rism:referencesNotes": {
        "label": "references and notes section",
        "range": ["rism:ReferencesNotesSection"],
        "query_patterns": ["?record rism:referencesNotes/rism:hasNote ?note ."],
    },
    "rism:notes": {"label": "notes section", "range": ["rism:NotesSection"]},
    "rism:hasNote": {
        "label": "has note",
        "comment": "Links a notes or references-and-notes section to a note node that typically carries rdfs:label and rdf:value.",
    },
    "rism:externalResources": {
        "label": "external resources section",
        "range": ["rism:ExternalResourcesSection"],
        "query_patterns": [
            "?record rism:externalResources/rism:hasExternalResource ?resource ."
        ],
    },
    "rism:hasExternalResource": {
        "label": "has external resource",
        "range": ["rism:ExternalResource"],
    },
    "rism:hasExternalRecord": {
        "label": "has external record",
        "range": ["rism:ExternalRecord"],
    },
    "rism:externalAuthorities": {
        "label": "external authorities section",
        "range": ["rism:ExternalAuthoritiesSection"],
        "query_patterns": [
            "?record rism:externalAuthorities/rism:hasExternalAuthority ?authority ."
        ],
    },
    "rism:hasExternalAuthority": {
        "label": "has external authority",
        "range": ["rism:ExternalAuthority"],
        "service_notes": [
            "This predicate is used both for section items under rism:externalAuthorities and for top-level authorityLinks emitted through properties."
        ],
    },
    "rism:digitalObjects": {
        "label": "digital objects section",
        "range": ["rism:DigitalObjectsSection"],
    },
    "rism:hasDigitalObject": {
        "label": "has digital object",
        "range": ["rism:DigitalObject"],
    },
    "rism:works": {
        "label": "works section or relation",
        "comment": "Depending on context, links a resource to a works section, a nested works wrapper, or a concrete work node.",
    },
    "rism:hasWork": {"label": "has work", "range": ["rism:Work"]},
    "rism:workReferences": {"label": "work references section"},
    "rism:hasWorkNode": {"label": "has work node"},
    "rism:worksCatalogs": {"label": "works catalogs section"},
    "rism:hasWorkCatalogReference": {"label": "has work catalog reference"},
    "rism:composer": {"label": "composer", "range": ["rism:Person"]},
    "rism:hasLocation": {
        "label": "has location",
        "range": ["rism:LocationAddressSection"],
    },
    "rdf:value": {
        "label": "value",
        "property_type": "datatype",
        "comment": (
            "Generic literal value used throughout the service for summary items, "
            "note content, status codes, external authority identifiers, and labels "
            "such as subject terms."
        ),
    },
    "rism:sectionLabel": {
        "label": "section label",
        "property_type": "datatype",
        "comment": "A human-readable translated label on a section node.",
    },
    "rism:hasSummary": {
        "property_type": "object",
        "label": "has summary",
        "comment": (
            "Links a record or structural node to a summary node, usually carrying "
            "rdfs:label and rdf:value, and sometimes classification types such as "
            "dcterms:type or pmo:MediumOfPerformance."
        ),
        "query_patterns": [
            "?record rism:hasSummary ?summary . ?summary rdf:value ?value ."
        ],
    },
    "rism:hasDates": {
        "property_type": "object",
        "label": "has dates",
        "comment": "Links a record to a date wrapper node with earliest/latest numeric dates and a date statement.",
        "query_patterns": ["?record rism:hasDates/rism:earliestDate ?from ."],
    },
    "rism:earliestDate": {"label": "earliest date", "property_type": "datatype"},
    "rism:latestDate": {"label": "latest date", "property_type": "datatype"},
    "rism:dateStatement": {"label": "date statement", "property_type": "datatype"},
    "rism:hasKeyMode": {"label": "key or mode", "property_type": "datatype"},
    "rism:hasPhysicalDimensions": {
        "label": "physical dimensions",
        "property_type": "datatype",
    },
    "rism:hasSiglum": {"label": "siglum", "property_type": "datatype"},
    "rism:hasCountryCodes": {"label": "country codes", "property_type": "datatype"},
    "rism:hasCityName": {"label": "city name", "property_type": "datatype"},
    "rism:holdingType": {
        "label": "holding type",
        "property_type": "datatype",
        "comment": 'Current service RDF emits holdingType as a literal naming a holding class, for example "rism:PrintHolding".',
    },
    "rism:hasPAEClef": {"label": "PAE clef", "property_type": "datatype"},
    "rism:hasPAEKeysig": {"label": "PAE key signature", "property_type": "datatype"},
    "rism:hasPAETimesig": {"label": "PAE time signature", "property_type": "datatype"},
    "rism:hasPAEData": {"label": "PAE notation data", "property_type": "datatype"},
    "rism:paeEncoding": {"label": "PAE encoding", "property_type": "datatype"},
    "rism:meiEncoding": {"label": "MEI encoding URL", "property_type": "datatype"},
    "rism:authorityScheme": {"label": "authority scheme", "property_type": "datatype"},
    "rism:authorityBase": {"label": "authority base URL", "property_type": "datatype"},
    "rism:authorityUrl": {"label": "authority URL", "property_type": "datatype"},
    "rism:totalItems": {"label": "total items", "property_type": "datatype"},
    "rism:website": {"label": "website", "property_type": "datatype"},
    "rism:emailAddress": {"label": "email address", "property_type": "datatype"},
    "schemaorg:address": {
        "property_type": "object",
        "label": "address",
        "comment": "Links an institution location section to a postal-address style node.",
    },
    "schemaorg:sameAs": {
        "property_type": "datatype",
        "label": "same as",
        "comment": "Top-level sameAs links exposed in properties for institutions and places.",
    },
}
IGNORED_CONTEXT_KEYS = {
    "@version",
    "@protected",
    "@vocab",
    "id",
    "type",
    "included",
    "properties",
}
PROPERTY_METADATA = {**BASE_PROPERTY_METADATA, **RELATIONSHIP_PROPERTY_METADATA}
RESERVED_OBJECT_MARKERS = {"@id", "@vocab"}
XSD_OR_JSON_PREFIXES = ("xsd:", "@json")
OUTPUT_PATH = PROJECT_ROOT / "docs" / "ontology" / "rism-service-ontology.ttl"


def configure_logging() -> logging.Logger:
    logging_path = SCRIPT_DIR / "logging.yml"
    if logging_path.exists():
        with logging_path.open() as logging_file:
            config = yaml.safe_load(logging_file)
        logging.config.dictConfig(config)
    return logging.getLogger("ontology")


log = configure_logging()


def resolve_term(term: str) -> str:
    if term.startswith("http://") or term.startswith("https://"):
        return term
    if ":" not in term:
        return PREFIXES["rism"] + term
    prefix, local = term.split(":", 1)
    return PREFIXES[prefix] + local


def node(term: str) -> NamedNode:
    return NamedNode(resolve_term(term))


def local_name(term: str) -> str:
    iri = resolve_term(term)
    if "#" in iri:
        return iri.rsplit("#", 1)[1]
    return iri.rstrip("/").rsplit("/", 1)[1]


def human_label(term: str) -> str:
    local = local_name(term)
    chars: list[str] = []
    for index, char in enumerate(local):
        if index and char.isupper() and local[index - 1].islower():
            chars.append(" ")
        chars.append(char)
    return "".join(chars).replace("_", " ").strip().capitalize()


def literal_quad(
    subject: str,
    predicate: str,
    value: str,
    *,
    language: str | None = "en",
) -> Quad:
    literal = Literal(value, language=language) if language else Literal(value)
    return Quad(node(subject), node(predicate), literal, DefaultGraph())


def resource_quad(subject: str, predicate: str, obj: str) -> Quad:
    return Quad(node(subject), node(predicate), node(obj), DefaultGraph())


def context_entries(ctx: dict[str, Any]) -> Iterable[tuple[str, Any]]:
    for key, value in ctx.items():
        if key in IGNORED_CONTEXT_KEYS:
            continue
        yield key, value


def empty_term_metadata() -> dict[str, Any]:
    return {
        "property_types": set(),
        "contexts": set(),
        "containers": set(),
        "coercions": set(),
        "nested_context": False,
    }


def merge_term_metadata(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    return {
        "property_types": set(base.get("property_types", set()))
        | set(extra.get("property_types", set())),
        "contexts": set(base.get("contexts", set()))
        | set(extra.get("contexts", set())),
        "containers": set(base.get("containers", set()))
        | set(extra.get("containers", set())),
        "coercions": set(base.get("coercions", set()))
        | set(extra.get("coercions", set())),
        "nested_context": bool(base.get("nested_context", False))
        or bool(extra.get("nested_context", False)),
    }


def merge_term_maps(
    left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    merged = {
        term: merge_term_metadata(empty_term_metadata(), metadata)
        for term, metadata in left.items()
    }
    for term, metadata in right.items():
        merged[term] = merge_term_metadata(
            merged.get(term, empty_term_metadata()), metadata
        )
    return merged


def collect_terms() -> dict[str, dict[str, Any]]:
    terms: dict[str, dict[str, Any]] = {}
    for context_name, context in CONTEXTS.items():
        # The JSON-LD contexts are still the source of truth for which service
        # predicates exist; curated metadata only enriches their ontology docs.
        terms = merge_term_maps(terms, walk_context(context, context_name=context_name))
    return terms


def metadata_from_context_value(
    value: dict[str, Any], *, context_name: str
) -> dict[str, Any]:
    metadata = empty_term_metadata()
    metadata["contexts"] = {context_name}

    container = value.get("@container")
    if isinstance(container, list):
        metadata["containers"] = {str(item) for item in container}
    elif isinstance(container, str):
        metadata["containers"] = {container}

    coercion = value.get("@type")
    if isinstance(coercion, str):
        metadata["coercions"] = {coercion}

    nested_context = value.get("@context")
    if isinstance(nested_context, dict):
        metadata["nested_context"] = True
        metadata["property_types"] = {"object"}
    elif coercion in RESERVED_OBJECT_MARKERS:
        metadata["property_types"] = {"object"}
    elif coercion and coercion.startswith(XSD_OR_JSON_PREFIXES):
        metadata["property_types"] = {"datatype"}
    else:
        metadata["property_types"] = {"datatype"}

    return metadata


def walk_context(
    ctx: dict[str, Any], *, context_name: str
) -> dict[str, dict[str, Any]]:
    terms: dict[str, dict[str, Any]] = {}
    for _, value in context_entries(ctx):
        if value is None or value == "@nest":
            continue
        if isinstance(value, str):
            continue
        if not isinstance(value, dict):
            continue
        iri = value.get("@id")
        if not isinstance(iri, str) or iri == "@nest":
            nested = value.get("@context")
            if isinstance(nested, dict):
                terms = merge_term_maps(
                    terms, walk_context(nested, context_name=context_name)
                )
            continue

        term_map = {iri: metadata_from_context_value(value, context_name=context_name)}
        nested_context = value.get("@context")
        if isinstance(nested_context, dict):
            term_map = merge_term_maps(
                term_map, walk_context(nested_context, context_name=context_name)
            )
        terms = merge_term_maps(terms, term_map)
    return terms


def inferred_property_type(term: str, metadata: dict[str, Any]) -> str:
    curated_type = PROPERTY_METADATA.get(term, {}).get("property_type")
    if curated_type:
        return curated_type
    property_types = metadata.get("property_types", set())
    if "object" in property_types and "datatype" not in property_types:
        return "object"
    if "datatype" in property_types and "object" not in property_types:
        return "datatype"
    if "object" in property_types:
        return "object"
    return "datatype"


def ontology_header_quads() -> list[Quad]:
    subject = ONTOLOGY_METADATA["iri"]
    quads = [
        resource_quad(subject, "rdf:type", "owl:Ontology"),
        literal_quad(subject, "dcterms:title", ONTOLOGY_METADATA["title"]),
        literal_quad(subject, "dcterms:description", ONTOLOGY_METADATA["description"]),
        literal_quad(
            subject, "owl:versionInfo", ONTOLOGY_METADATA["version"], language=""
        ),
        literal_quad(subject, "rdfs:comment", ONTOLOGY_METADATA["comment"]),
    ]
    quads.extend(
        resource_quad(subject, "rdfs:seeAlso", link)
        for link in ONTOLOGY_METADATA["see_also"]
    )
    return quads


def label_and_comment_quads(subject: str, metadata: dict[str, Any]) -> list[Quad]:
    quads = [
        literal_quad(subject, "rdfs:label", metadata.get("label", human_label(subject)))
    ]
    comment = metadata.get("comment")
    if isinstance(comment, str):
        quads.append(literal_quad(subject, "rdfs:comment", comment))
    return quads


def term_annotation_quads(subject: str, metadata: dict[str, Any]) -> list[Quad]:
    quads = [
        literal_quad(subject, "rism:queryPattern", pattern, language=None)
        for pattern in metadata.get("query_patterns", [])
    ]
    quads.extend(
        literal_quad(subject, "rism:serviceNote", note)
        for note in metadata.get("service_notes", [])
    )
    return quads


def class_quads() -> list[Quad]:
    quads: list[Quad] = []
    for term, metadata in CLASS_METADATA.items():
        quads.append(resource_quad(term, "rdf:type", "owl:Class"))
        quads.extend(label_and_comment_quads(term, metadata))
        quads.extend(
            resource_quad(term, "rdfs:subClassOf", parent)
            for parent in metadata.get("subclass_of", [])
        )
        quads.extend(
            resource_quad(term, "owl:equivalentClass", equivalent)
            for equivalent in metadata.get("equivalent_classes", [])
        )
        quads.extend(
            resource_quad(term, "skos:exactMatch", match)
            for match in metadata.get("exact_matches", [])
        )
        quads.extend(term_annotation_quads(term, metadata))
    return quads


def property_quads(term_data: dict[str, dict[str, Any]]) -> list[Quad]:
    # Emit both context-derived predicates and local curated terms that do not
    # appear directly in the JSON-LD contexts, such as helper relationship roles.
    all_terms = sorted(set(term_data) | set(PROPERTY_METADATA))
    quads: list[Quad] = []
    for term in all_terms:
        metadata = PROPERTY_METADATA.get(term, {})
        property_type = inferred_property_type(term, term_data.get(term, {}))
        owl_type = {
            "annotation": "owl:AnnotationProperty",
            "object": "owl:ObjectProperty",
            "datatype": "owl:DatatypeProperty",
        }[property_type]
        quads.append(resource_quad(term, "rdf:type", owl_type))
        quads.extend(label_and_comment_quads(term, metadata))
        quads.extend(
            resource_quad(term, "rdfs:subPropertyOf", parent)
            for parent in metadata.get("subproperty_of", [])
        )
        quads.extend(
            resource_quad(term, "rdfs:domain", domain)
            for domain in metadata.get("domain", [])
        )
        quads.extend(
            resource_quad(term, "rdfs:range", range_term)
            for range_term in metadata.get("range", [])
        )
        quads.extend(
            resource_quad(term, "owl:equivalentProperty", equivalent)
            for equivalent in metadata.get("equivalent_properties", [])
        )
        quads.extend(
            resource_quad(term, "owl:inverseOf", inverse)
            for inverse in metadata.get("inverse_of", [])
        )
        quads.extend(
            resource_quad(term, "skos:exactMatch", match)
            for match in metadata.get("exact_matches", [])
        )
        quads.extend(term_annotation_quads(term, metadata))
    return quads


def sorted_quads(quads: Iterable[Quad]) -> list[Quad]:
    def datatype_value(obj: Any) -> str:
        datatype = getattr(obj, "datatype", None)
        return datatype.value if datatype is not None else ""  # type: ignore

    return sorted(
        quads,
        key=lambda quad: (
            quad.subject.value,
            quad.predicate.value,
            quad.object.value,
            getattr(quad.object, "language", "") or "",
            datatype_value(quad.object),
        ),
    )


def serialize_ontology() -> str:
    quads = [
        *ontology_header_quads(),
        *class_quads(),
        *property_quads(collect_terms()),
    ]
    serialized = serialize(
        sorted_quads(quads), format=RdfFormat.TURTLE, prefixes=PREFIXES
    )
    if serialized is None:
        raise RuntimeError("Ontology serialization returned no Turtle output")

    if isinstance(serialized, (bytes, bytearray)):
        output = serialized.decode("utf-8")
    elif isinstance(serialized, str):
        output = serialized
    else:
        raise RuntimeError("Ontology serialization returned an unexpected value")

    turtle = output if output.endswith("\n") else f"{output}\n"
    try:
        # Reuse the same pretty-printer as the request-time Turtle exporter so
        # the checked-in ontology stays easy to diff and read.
        formatted = format_turtle(turtle)
        return formatted if formatted.endswith("\n") else f"{formatted}\n"
    except PrttlError:
        log.exception(
            "Ontology Turtle pretty-printing failed; returning raw Turtle output"
        )
        return turtle
    except BaseException:
        log.exception(
            "Ontology Turtle pretty-printing panicked; returning raw Turtle output"
        )
        return turtle


def write_ontology(output_path: Path) -> str:
    turtle = serialize_ontology()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(turtle)
    return turtle


def check_ontology(output_path: Path) -> int:
    expected = serialize_ontology()
    if not output_path.exists():
        log.error("Ontology file does not exist: %s", output_path)
        return 1
    actual = output_path.read_text()
    if actual != expected:
        log.error("Ontology drift detected for %s", output_path)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the RISM service ontology.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Write ontology Turtle to this path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit nonzero if the generated ontology differs from the target file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check:
        return check_ontology(args.output)
    write_ontology(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
