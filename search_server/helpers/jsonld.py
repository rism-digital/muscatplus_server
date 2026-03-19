from typing import NamedTuple

from search_server.helpers.identifiers import RISM_RELATIONSHIP_BASE

# Create a type for Context Documents
ContextDocument = dict

__BASE_CONTEXT = {
    "@version": 1.1,
    "@protected": True,
    "@vocab": "https://rism.online/api/v1#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rism": "https://rism.online/api/v1#",
    "rismrel": f"{RISM_RELATIONSHIP_BASE}",
    # "rismdata": "https://rism.online/api/datatypes-v1#",
    "pmo": "http://performedmusicontology.org/ontology/",
    "relators": "http://id.loc.gov/vocabulary/relators/",
    "dcterms": "http://purl.org/dc/terms/",
    # "dctypes": "http://purl.org/dc/dcmitype/",
    # "as": "http://www.w3.org/ns/activitystreams#",
    # "hydra": "http://www.w3.org/ns/hydra/core#",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "geojson": "https://purl.org/geojson/vocab#",
    "schemaorg": "https://schema.org/",
    "rdau": "http://rdaregistry.info/Elements/u/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "type": "@type",
    "id": "@id",
    # "none": "@none",
    "label": {
        "@id": "rdfs:label",
        "@container": ["@language", "@set"],
    },
    "value": {
        "@id": "rdf:value",
        "@container": ["@language", "@set"],
    },
}

__RELATIONSHIPS = {
    "relationships": {
        "@id": "rism:hasRelationship",
        "@type": "@id",
        "@context": {
            "items": "@set",
            "role": {
                "@id": "rism:hasRole",
            },
            "qualifier": {
                "@id": "rism:hasQualifier",
                "@type": "@vocab",
            },
            "relatedTo": {
                "@id": "dcterms:relation",
            },
        },
    }
}

__INCIPITS = {
    "incipits": {
        "@id": "rism:hasIncipit",
        "@type": "@id",
        "@context": {
            "items": "@set",
            "properties": "@nest",
            "clef": {"@id": "rism:hasPAEClef"},
            "keysig": {"@id": "rism:hasPAEKeysig"},
            "timesig": {"@id": "rism:hasPAETimesig"},
            "notation": {"@id": "rism:hasPAEData"},
            "encodings": {
                "@id": "rism:hasEncoding",
                "@container": "@set",
                "@context": {
                    "data": {
                        "@id": "rism:paeEncoding",
                        "@type": "@json",
                    },
                    "url": {
                        "@id": "rism:meiEncoding",
                        "@type": "xsd:anyURI",
                    },
                },
            },
            "partOf": {
                "@value": "null",
                "propagate": "false",
            },
        },
    }
}

__PARTOF = {
    "partOf": {
        "@id": "rism:isPartOf",
        "@type": "@id",
        "@context": {
            "items": "@set",
            "relationshipType": {
                "@id": "rism:workCatalogRelationship",
                "@type": "@vocab",
            },
            "workNumber": {"@id": "rism:hasWorkNumber"},
            "relatedTo": {"@id": "rism:Publication"},
        },
    },
}

__CREATOR = {
    "creator": {
        "@id": "dcterms:creator",
        "@type": "@id",
        "@context": {"relatedTo": "@nest"},
    }
}

__SUMMARY = {
    "summary": {
        "@id": "rism:hasSummary",
        "@type": "@id",
    }
}

__DATES = {
    "dates": {
        "@id": "rism:hasDates",
        "@context": {
            "earliestDate": {
                "@id": "rism:earliestDate",
                "@type": "xsd:integer",
            },
            "latestDate": {
                "@id": "rism:latestDate",
                "@type": "xsd:integer",
            },
            "dateStatement": {
                "@id": "rism:dateStatement",
            },
        },
    },
}

__PROPERTIES = {
    "properties": "@nest",
    "keyMode": {
        "@id": "rism:hasKeyMode",
    },
    "physicalDimensions": {
        "@id": "rism:hasPhysicalDimensions",
        "@container": "@list",
    },
}

RISM_JSONLD_DEFAULT_CONTEXT: ContextDocument = {**__BASE_CONTEXT}
RISM_JSONLD_PERSON_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__RELATIONSHIPS,
    "typeLabel": {
        "@id": "rism:typeLabel",
        "@container": ["@language", "@set"],
    },
    "sectionLabel": {
        "@id": "rism:sectionLabel",
        "@container": ["@language", "@set"],
    },
    "recordHistory": {
        "@id": "rism:recordHistory",
        "@type": "@id",
        "@context": {
            "created": {
                "@id": "dcterms:created",
                "@type": "@id",
            },
            "updated": {
                "@id": "dcterms:modified",
                "@type": "@id",
            },
            "value": {
                "@id": "rdf:value",
                "@type": "xsd:dateTime",
            },
        },
    },
    "biographicalDetails": {
        "@id": "rism:biographicalDetails",
        "@type": "@id",
        "@context": {"summary": {"@id": "rism:hasSummary", "@container": "@set"}},
    },
    "externalAuthorities": {
        "@id": "rism:externalAuthorities",
        "@type": "@id",
        "@context": {"items": {"@id": "rism:hasItem", "@container": "@set"}},
    },
    "nameVariants": {
        "@id": "rism:nameVariants",
        "@type": "@id",
        "@context": {"items": {"@id": "rism:hasItem", "@container": "@set"}},
    },
    "notes": {
        "@id": "rism:notes",
        "@type": "@id",
        "@context": {"notes": {"@id": "rism:hasNote", "@container": "@set"}},
    },
    "works": {
        "@id": "rism:works",
        "@type": "@id",
        "@context": {
            "workReferences": {"@id": "rism:workReferences", "@type": "@id"},
            "worksCatalogs": {"@id": "rism:worksCatalogs", "@type": "@id"},
            "items": {"@id": "rism:hasItem", "@container": "@set"},
        },
    },
}

RISM_JSONLD_INSTITUTION_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    "properties": "@nest",
    "siglum": {
        "@id": "rism:hasSiglum",
    },
    "countryCodes": {
        "@id": "rism:hasCountryCodes",
        "@container": "@set",
    },
    "city": {
        "@id": "rism:hasCityName",
    },
    "location": {
        "@id": "rism:hasLocation",
        "@type": "@id",
        "@context": {
            "coordinates": {"@id": "geojson:coordinates"},
            "geometry": {"@id": "geojson:geometry", "@type": "@id"},
            "lat": {"@id": "geo:lat", "@type": "xsd:float"},
            "long": {"@id": "geo:long", "@type": "xsd:float"},
        },
    },
}

RISM_JSONLD_WORK_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__INCIPITS,
    **__PARTOF,
    **__CREATOR,
    **__SUMMARY,
    **__DATES,
    **__PROPERTIES,
}

RISM_JSONLD_PUBLICATION_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__SUMMARY,
    **__RELATIONSHIPS,
}

RISM_JSONLD_SOURCE_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__RELATIONSHIPS,
    **__INCIPITS,
    **__PARTOF,
    **__CREATOR,
    **__DATES,
    **__PROPERTIES,
    "materialGroups": {
        "@id": "rism:hasMaterialGroup",
        "@type": "@id",
        "@context": {
            "items": "@set",
            **__SUMMARY,
        },
    },
    "sourceItems": {
        "@id": "rism:hasSourceItem",
        "@type": "@id",
        "@context": {"items": "@set"},
    },
    "exemplars": {
        "@id": "rism:hasHolding",
        "@type": "@id",
        "@context": {
            "items": "@set",
            "heldBy": {"@id": "rism:hasHoldingInstitution"},
        },
    },
    "contents": {
        "@id": "@nest",
    },
    "subjects": {
        "@id": "rism:hasSubject",
        "@type": "@id",
        "@context": {"items": "@set"},
    },
    "properties": "@nest",
    "keyMode": {
        "@id": "rism:hasKeyMode",
    },
    "physicalDimensions": {
        "@id": "rism:hasPhysicalDimensions",
        "@container": "@list",
    },
}


class RouteOptions(NamedTuple):
    route: str
    context: dict


# The route is set in the 'routes' and represents the route for a record of a given type,
# e.g., "mp_server.people.person" is defined in "routes/people" and is the "person" function.
# The context is the route given in "routes/api" and represents the URL to the context
# document. A configuration parameter and a header ("X-Embed-Context") can control whether the
# JSON-LD is served with an embedded context, or just a URL to the context document. (An embedded
# context is used to transform the JSON-LD into RDF).
RouteContextMap: dict[str, RouteOptions] = {
    "mp_server.people.person": RouteOptions(
        "api.person_context", RISM_JSONLD_PERSON_CONTEXT
    ),
    "mp_server.institutions.institution": RouteOptions(
        "api.institution_context", RISM_JSONLD_INSTITUTION_CONTEXT
    ),
    "mp_server.sources.source": RouteOptions(
        "api.source_context", RISM_JSONLD_SOURCE_CONTEXT
    ),
    "mp_server.works.work": RouteOptions("api.work_context", RISM_JSONLD_WORK_CONTEXT),
    "mp_server.publications.publication": RouteOptions(
        "api.publication_context", RISM_JSONLD_PUBLICATION_CONTEXT
    ),
    "__default": RouteOptions("api.default_context", RISM_JSONLD_DEFAULT_CONTEXT),
}
