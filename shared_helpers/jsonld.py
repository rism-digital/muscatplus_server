from collections import namedtuple

# Create a type for Context Documents
ContextDocument = dict

__BASE_CONTEXT = {
    "@version": 1.1,
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rism": "https://rism.online/api/v1#",
    # "rismdata": "https://rism.online/api/datatypes-v1#",
    # "pmo": "http://performedmusicontology.org/ontology/",
    "relators": "http://id.loc.gov/vocabulary/relators/",
    "dcterms": "http://purl.org/dc/terms/",
    # "dctypes": "http://purl.org/dc/dcmitype/",
    # "as": "http://www.w3.org/ns/activitystreams#",
    # "hydra": "http://www.w3.org/ns/hydra/core#",
    # "geojson": "https://purl.org/geojson/vocab#",
    "schemaorg": "https://schema.org/",
    "rdau": "http://rdaregistry.info/Elements/u/",
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

RISM_JSONLD_DEFAULT_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT
}


RISM_JSONLD_PERSON_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT
}


RISM_JSONLD_SOURCE_CONTEXT: ContextDocument = {
    **__BASE_CONTEXT,
    "relationships": {
        "@id": "rism:Relationships",
        "@nest": "relationships",
        "@context": {
            "items": {
                "@id": "rdf:Bag",
                "@type": "@id",
                "@container": "@graph"
            },
            "role": {
                "@id": "dcterms:relation",
                "@type": "@vocab"
            },
            "qualifier": {
                "@id": "rism:Qualifier"
            },
            "relatedTo": {
                "@id": "schemaorg:agent"
            }
        }
    },
    "creator": {
        "@id": "rism:Relationships",
        "@nest": "relationships",
        # "@type": "@id",
        # "@nest": "creator",
        "@context": {
            "role": {
                "@id": "dcterms:relation",
                "@type": "@vocab"
            },
            "qualifier": {
                "@id": "rism:Qualifier"
            },
            "relatedTo": {
                "@id": "schemaorg:agent",
                "@type": "vocab"
            }
        }
    }
    # "summary": {
    #     "@id": "rism:Summary",
    #     "@type": "@id"
    # },
}


RouteOptions = namedtuple("RouteOptions", ["route", "context"])

RouteContextMap: dict[str, RouteOptions] = {
    "mp_server.people.person": RouteOptions("person_context", RISM_JSONLD_PERSON_CONTEXT),
    "mp_server.sources.source": RouteOptions("source_context", RISM_JSONLD_SOURCE_CONTEXT),
    "__default": RouteOptions("default_context", RISM_JSONLD_DEFAULT_CONTEXT)
}
