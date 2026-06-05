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
        "@protected": False,
    },
}

__RELATIONSHIPS = {
    "relationships": {
        "@id": "rism:relationships",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasRelationship", "@container": "@set"},
            "role": {"@id": "rism:hasRole", "@type": "@vocab"},
            "qualifier": {
                "@id": "rism:hasQualifier",
                "@type": "@vocab",
            },
            "relatedTo": {"@id": "dcterms:relation", "@type": "@id"},
        },
    }
}

__INCIPITS = {
    "incipits": {
        "@id": "rism:incipits",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasIncipit", "@container": "@set"},
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
            "rendered": None,
            "partOf": {"@id": "rism:isPartOf", "@type": "@id"},
        },
    }
}

__PARTOF = {
    "partOf": {
        "@id": "rism:partOf",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:isPartOf", "@container": "@set"},
            "relationshipType": {
                "@id": "rism:workCatalogRelationship",
                "@type": "@vocab",
            },
            "workNumber": {"@id": "rism:hasWorkNumber"},
            "relatedTo": {"@id": "dcterms:relation", "@type": "@id"},
        },
    },
}

__CREATOR = {
    "creator": {
        "@id": "dcterms:creator",
        "@type": "@id",
        "@context": {
            "role": {"@id": "rism:hasRole", "@type": "@vocab"},
            "relatedTo": {"@id": "dcterms:relation", "@type": "@id"},
        },
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

__TYPE_LABEL = {
    "typeLabel": {
        "@id": "rism:typeLabel",
        "@container": ["@language", "@set"],
    }
}

__SECTION_LABEL = {
    "sectionLabel": {
        "@id": "rism:sectionLabel",
        "@container": ["@language", "@set"],
    }
}

__RECORD_HISTORY = {
    "recordHistory": {
        "@id": "rism:recordHistory",
        "@type": "@id",
        "@context": {
            "created": {"@id": "dcterms:created", "@type": "xsd:dateTime"},
            "updated": {"@id": "dcterms:modified", "@type": "xsd:dateTime"},
            "value": {
                "@id": "rdf:value",
                "@type": "xsd:dateTime",
                "@protected": False,
            },
        },
    }
}

RISM_JSONLD_DEFAULT_CONTEXT: ContextDocument = {**__BASE_CONTEXT}
RISM_JSONLD_PERSON_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__RELATIONSHIPS,
    **__TYPE_LABEL,
    **__SECTION_LABEL,
    **__RECORD_HISTORY,
    "biographicalDetails": {
        "@id": "rism:biographicalDetails",
        "@type": "@id",
        "@context": {"summary": {"@id": "rism:hasSummary", "@container": "@set"}},
    },
    "externalAuthorities": {
        "@id": "rism:externalAuthorities",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasExternalAuthority", "@container": "@set"}
        },
    },
    "nameVariants": {
        "@id": "rism:nameVariants",
        "@type": "@id",
        "@context": {"items": {"@id": "rism:hasNameVariant", "@container": "@set"}},
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
            "workReferences": {
                "@id": "rism:workReferences",
                "@type": "@id",
                "@context": {
                    "items": {"@id": "rism:hasWorkNode", "@container": "@set"}
                },
            },
            "worksCatalogs": {
                "@id": "rism:worksCatalogs",
                "@type": "@id",
                "@context": {
                    "items": {
                        "@id": "rism:hasWorkCatalogReference",
                        "@container": "@set",
                    }
                },
            },
            "works": {
                "@id": "rism:works",
                "@type": "@id",
                "@context": {
                    "items": {"@id": "rism:hasWork", "@container": "@set"}
                },
            },
            "items": {"@id": "rism:hasWork", "@container": "@set"},
        },
    },
    "externalResources": {
        "@id": "rism:externalResources",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasExternalResource", "@container": "@set"},
            "externalRecords": {
                "@id": "rism:hasExternalRecord",
                "@container": "@set",
                "@type": "@id",
            },
        },
    },
    "digitalObjects": {
        "@id": "rism:digitalObjects",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasDigitalObject", "@container": "@set"}
        },
    },
}

RISM_JSONLD_INSTITUTION_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__RELATIONSHIPS,
    **__TYPE_LABEL,
    **__SECTION_LABEL,
    "organizationDetails": {
        "@id": "rism:organizationDetails",
        "@type": "@id",
        "@context": {"summary": {"@id": "rism:hasSummary", "@container": "@set"}},
    },
    **__RECORD_HISTORY,
    "sources": {
        "@id": "rism:sources",
        "@type": "@id",
        "@context": {
            "totalItems": {
                "@id": "rism:totalItems",
                "@type": "xsd:integer",
            },
        },
    },
    "externalAuthorities": {
        "@id": "rism:externalAuthorities",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasExternalAuthority", "@container": "@set"}
        },
    },
    "notes": {
        "@id": "rism:notes",
        "@type": "@id",
        "@context": {"notes": {"@id": "rism:hasNote", "@container": "@set"}},
    },
    "externalResources": {
        "@id": "rism:externalResources",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasExternalResource", "@container": "@set"},
            "externalRecords": {
                "@id": "rism:hasExternalRecord",
                "@container": "@set",
                "@type": "@id",
            },
        },
    },
    "digitalObjects": {
        "@id": "rism:digitalObjects",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasDigitalObject", "@container": "@set"}
        },
    },
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
            **__SECTION_LABEL,
            "addresses": {"@id": "rism:addresses", "@container": "@set"},
            "website": {"@id": "rism:website"},
            "email": {"@id": "rism:emailAddress"},
            "coordinates": {"@id": "geojson:coordinates", "@container": "@list"},
            "geometry": {"@id": "geojson:geometry", "@type": "@id"},
            "lat": {"@id": "geo:lat", "@type": "xsd:float"},
            "long": {"@id": "geo:long", "@type": "xsd:float"},
        },
    },
}

RISM_JSONLD_WORK_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__RELATIONSHIPS,
    **__INCIPITS,
    **__PARTOF,
    **__CREATOR,
    **__SUMMARY,
    **__DATES,
    **__PROPERTIES,
    **__TYPE_LABEL,
    **__SECTION_LABEL,
    **__RECORD_HISTORY,
    "sources": {
        "@id": "rism:sources",
        "@type": "@id",
        "@context": {
            **__SECTION_LABEL,
            "totalItems": {"@id": "rism:totalItems", "@type": "xsd:integer"},
        },
    },
    "formOfWork": {
        "@id": "rism:formOfWork",
        "@type": "@id",
        "@context": {"items": {"@id": "rism:hasFormOfWork", "@container": "@set"}},
    },
    "referencesNotes": {
        "@id": "rism:referencesNotes",
        "@type": "@id",
        "@context": {
            "notes": {"@id": "rism:hasNote", "@container": "@set"},
            "performanceLocations": {
                "@id": "rism:performanceLocations",
                "@type": "@id",
                "@container": "@set",
            },
            "liturgicalFestivals": {
                "@id": "rism:liturgicalFestivals",
                "@type": "@id",
                "@container": "@set",
            },
        },
    },
    "externalAuthorities": {
        "@id": "rism:externalAuthorities",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasExternalAuthority", "@container": "@set"}
        },
    },
    "externalResources": {
        "@id": "rism:externalResources",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasExternalResource", "@container": "@set"},
            "externalRecords": {
                "@id": "rism:hasExternalRecord",
                "@container": "@set",
                "@type": "@id",
            }
        },
    },
}

RISM_JSONLD_PUBLICATION_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__SUMMARY,
    **__RELATIONSHIPS,
    **__CREATOR,
    **__TYPE_LABEL,
    **__SECTION_LABEL,
    **__RECORD_HISTORY,
    "composer": {
        "@id": "rism:composer",
        "@type": "@id",
    },
    "properties": {
        "@id": "@nest",
    },
    "shortTitle": {
        "@id": "rism:shortTitle",
        "@container": ["@language", "@set"],
    },
    "publicationDates": {
        "@id": "rism:publicationDates",
        "@container": ["@language", "@set"],
    },
    "status": {
        "@id": "rism:status",
        "@type": "@id",
        "@context": {
            "label": {
                "@id": "rdfs:label",
                "@container": ["@language", "@set"],
            },
            "value": {"@id": "rdf:value"},
        },
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
            **__SECTION_LABEL,
            "url": {"@id": "schemaorg:url", "@type": "xsd:anyURI"},
            "totalItems": {"@id": "rism:totalItems", "@type": "xsd:integer"},
        },
    },
    "externalResources": {
        "@id": "rism:externalResources",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasExternalResource", "@container": "@set"},
            "externalRecords": {
                "@id": "rism:hasExternalRecord",
                "@container": "@set",
                "@type": "@id",
            },
        },
    },
}

RISM_JSONLD_SOURCE_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__RELATIONSHIPS,
    **__INCIPITS,
    **__PARTOF,
    **__CREATOR,
    **__SUMMARY,
    **__DATES,
    **__PROPERTIES,
    **__TYPE_LABEL,
    **__SECTION_LABEL,
    **__RECORD_HISTORY,
    "sourceTypes": {
        "@id": "rism:sourceTypes",
        "@type": "@id",
        "@context": {
            "recordType": {"@id": "rism:recordType", "@type": "@vocab"},
            "sourceType": {"@id": "rism:sourceType", "@type": "@vocab"},
            "contentTypes": {
                "@id": "rism:contentTypes",
                "@container": "@set",
                "@type": "@vocab",
            },
            "materialTypes": {
                "@id": "rism:materialTypes",
                "@container": "@set",
                "@type": "@vocab",
            },
        },
    },
    "materialGroups": {
        "@id": "rism:materialGroups",
        "@type": "@id",
        "@context": {
            **__SECTION_LABEL,
            "items": {"@id": "rism:hasMaterialGroup", "@container": "@set"},
            **__SUMMARY,
        },
    },
    "sourceItems": {
        "@id": "rism:sourceItems",
        "@type": "@id",
        "@context": {
            **__SECTION_LABEL,
            "url": {"@id": "schemaorg:url", "@type": "xsd:anyURI"},
            "totalItems": {"@id": "rism:totalItems", "@type": "xsd:integer"},
            "items": {"@id": "rism:hasSourceItem", "@container": "@set"},
        },
    },
    "exemplars": {
        "@id": "rism:holdings",
        "@type": "@id",
        "@context": {
            **__SECTION_LABEL,
            "items": {"@id": "rism:hasHolding", "@container": "@set"},
            "heldBy": {
                "@id": "rism:hasHoldingInstitution",
                "@type": "@id",
                "@context": {
                    "siglum": {"@id": "rism:hasSiglum"},
                    "countryCode": {"@id": "rism:hasCountryCodes"},
                    "city": {"@id": "rism:hasCityName"},
                },
            },
        },
    },
    "contents": {
        "@id": "@nest",
    },
    "subjects": {
        "@id": "rism:subjects",
        "@type": "@id",
        "@context": {
            **__SECTION_LABEL,
            "items": {"@id": "rism:hasSubject", "@container": "@set"},
        },
    },
    "referencesNotes": {
        "@id": "rism:referencesNotes",
        "@type": "@id",
        "@context": {
            "notes": {"@id": "rism:hasNote", "@container": "@set"},
            "performanceLocations": {
                "@id": "rism:performanceLocations",
                "@type": "@id",
            },
            "liturgicalFestivals": {"@id": "rism:liturgicalFestivals", "@type": "@id"},
        },
    },
    "externalResources": {
        "@id": "rism:externalResources",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasExternalResource", "@container": "@set"},
            "externalRecords": {
                "@id": "rism:hasExternalRecord",
                "@container": "@set",
                "@type": "@id",
            },
        },
    },
    "works": {
        "@id": "rism:works",
        "@type": "@id",
        "@context": {
            "workReference": {"@id": "rism:workReference", "@type": "@id"},
            "works": {
                "@id": "rism:works",
                "@type": "@id",
                "@context": {
                    "items": {"@id": "rism:hasWork", "@container": "@set"}
                },
            },
            "workReferences": {
                "@id": "rism:workReferences",
                "@type": "@id",
                "@context": {
                    "items": {"@id": "rism:hasWorkNode", "@container": "@set"}
                },
            },
            "worksCatalogs": {
                "@id": "rism:worksCatalogs",
                "@type": "@id",
                "@context": {
                    "items": {
                        "@id": "rism:hasWorkCatalogReference",
                        "@container": "@set",
                    }
                },
            },
        },
    },
    "digitalObjects": {
        "@id": "rism:digitalObjects",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasDigitalObject", "@container": "@set"}
        },
    },
    "inventoryItems": {
        "@id": "rism:inventoryItems",
        "@type": "@id",
        "@context": {
            "items": {"@id": "rism:hasInventoryItem", "@container": "@set"},
            "totalItems": {"@id": "rism:totalItems", "@type": "xsd:integer"},
        },
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
