from collections import namedtuple

# Create a type for Context Documents
ContextDocument = dict

__BASE_CONTEXT = {
    "@version": 1.1,
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rism": "https://rism.online/api/v1#",
    # "rismdata": "https://rism.online/api/datatypes-v1#",
    "pmo": "http://performedmusicontology.org/ontology/",
    "relators": "http://id.loc.gov/vocabulary/relators/",
    "dcterms": "http://purl.org/dc/terms/",
    # "dctypes": "http://purl.org/dc/dcmitype/",
    # "as": "http://www.w3.org/ns/activitystreams#",
    # "hydra": "http://www.w3.org/ns/hydra/core#",
    # "geojson": "https://purl.org/geojson/vocab#",
    "schemaorg": "https://schema.org/",
    "rdau": "http://rdaregistry.info/Elements/u/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "type": "@type",
    "id": "@id",
    # "none": "@none",
    "label": {
        "@id": "rdfs:label",
        "@container": [
            "@language",
            "@set"
        ]
    },
    "value": {
        "@id": "rdf:value",
        "@container": [
            "@language",
            "@set"
        ]
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
                "@type": "@vocab",
            },
            "qualifier": {
                "@id": "rism:hasQualifier",
                "@type": "@vocab",
            },
            "relatedTo": {
                "@id": "dcterms:relation",
            }
        }
    }
}

__INCIPITS = {
    "incipits": {
        "@id": "rism:hasIncipit",
        "@type": "@id",
        "@context": {
            "items": "@set",
            "properties": "@nest",
            "clef": {
                "@id": "rism:hasPAEClef"
            },
            "keysig": {
                "@id": "rism:hasPAEKeysig"
            },
            "timesig": {
                "@id": "rism:hasPAETimesig"
            },
            "notation": {
                "@id": "rism:hasPAEData"
            },
            "encodings": {
                "@id": "rism:hasEncoding",
                "@type": "@set",
                "@context": {
                    "data": {
                        "@id": "rism:paeEncoding",
                        "@type": "@json"
                    },
                    "url": {
                        "@id": "rism:meiEncoding",
                        "@type": "xsd:anyURI"
                    }
                }
            },
            "partOf": {"@value": "null", "propagate": "false"}
        },
    }
}


RISM_JSONLD_DEFAULT_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT
}


RISM_JSONLD_PERSON_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__RELATIONSHIPS
}


RISM_JSONLD_WORK_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT
}

RISM_JSONLD_SOURCE_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    **__RELATIONSHIPS,
    **__INCIPITS,
    "dates": {
        "@id": "rism:hasDates",
        "@context": {
            "earliestDate": {
                "@id": "rism:earliestDate",
                "@type": "xsd:integer"
            }
        }
    },
    "creator": {
        "@id": "dcterms:creator",
        "@type": "@id",
        "@context": {
            "relatedTo": "@nest"
        }
    },
    "materialGroups": {
        "@id": "rism:hasMaterialGroup",
        "@type": "@id",
        "@context": {
            "label": {"@value": "null", "@propagate": "false"},
            "items": "@set",
            "summary": {
                "@id": "rism:hasSummary",
                "@type": "@id",
            },
        },
    },
    "partOf": {
        "@id": "rism:isPartOf",
        "@type": "@id",
        "@context": {
            "label": {"@value": "null", "@propagate": "false"},
            "source": "@nest"
        }
    },
    "sourceItems": {
        "@id": "rism:hasSourceItem",
        "@type": "@id",
        "@context": {
            "label": {"@value": "null", "@propagate": "false"},
            "items": "@set"
        }
    },
    "exemplars": {
        "@id": "rism:hasHolding",
        "@type": "@id",
        "@context": {
            "label": {"@value": "null", "@propagate": "false"},
            "items": "@set",
            "heldBy": {
                "@id": "rism:hasHoldingInstitution"
            }
        }
    }
}

RouteOptions = namedtuple("RouteOptions", ["route", "context"])

RouteContextMap: dict[str, RouteOptions] = {
    "mp_server.people.person": RouteOptions("api.person_context", RISM_JSONLD_PERSON_CONTEXT),
    "mp_server.sources.source": RouteOptions("api.source_context", RISM_JSONLD_SOURCE_CONTEXT),
    "mp_server.works.work": RouteOptions("api.work_context", RISM_JSONLD_WORK_CONTEXT),
    "__default": RouteOptions("api.default_context", RISM_JSONLD_DEFAULT_CONTEXT)
}
