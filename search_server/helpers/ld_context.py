from typing import Dict

RISM_JSONLD_CONTEXT: Dict = {
    "@version": 1.1,
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rism": "https://rism.online/api/v1#",
    "rismdata": "https://rism.online/api/datatypes-v1#",
    "relators": "http://id.loc.gov/vocabulary/relators/",
    "dcterms": "http://purl.org/dc/terms/",
    "as": "http://www.w3.org/ns/activitystreams#",
    "hydra": "http://www.w3.org/ns/hydra/core#",
    "type": "@type",
    "id": "@id",
    "PartialCollectionView": "hydra:PartialCollectionView",
    "Collection": "hydra:Collection",
    "totalItems": "hydra:totalItems",
    "member": "hydra:member",
    "view": "hydra:view",
    "next": "hydra:next",
    "previous": "hydra:previous",
    "first": "hydra:first",
    "last": "hydra:last",

    "name": {
        "@id": "rdfs:label",
        "@container": [
            "@language",
            "@set"
        ],
        "@context": {
            "none": "@none"
        }
    },
    "seeAlso": {
        "@type": "@id",
        "@id": "rdfs:seeAlso",
        "@container": "@set"
    },
    "partOf": {
        "@id": "dcterms:partOf",
        "@type": "@id",
        "@container": "@set"
    },
    "profile": {
        "@type": "@vocab",
        "@id": "dcterms:conformsTo"
    },
    "musicIncipit": {
        "@id": "rdf:value",
        "@type": "rismdata:pae"  # a custom datatype IRI may not be recognized by some processors.
    },
    "textIncipit": {
        "@id": "rdf:value"
    },
    "items": {
        "@type": "@id",
        "@id": "as:items",
        "@container": "@list"
    }
}
