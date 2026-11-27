"""Query-driven IIIF Collections, independent of RISM JSON-LD serializers."""

import json
from collections.abc import AsyncIterator
from copy import deepcopy

from sanic.exceptions import NotFound
from sanic.log import logger
from small_asc.client import SolrError

from search_server.helpers.formatters import (
    format_institution_label,
    format_source_label,
)
from search_server.helpers.identifiers import get_identifier
from search_server.helpers.solr_connection import SolrConnection

IIIF_CONTEXT = "http://iiif.io/api/presentation/3/context.json"
MATERIALS = ("prints", "manuscripts", "other")
MATERIAL_LABEL_KEYS = {
    "prints": "rism_online.printed",
    "manuscripts": "rism_online.manuscript",
    "other": "records.other",
}
QUERY_PAGE_SIZE = 1000
MANIFEST_FIELDS = [
    "id",
    "source_id",
    "standard_titles_json",
    "main_title_s",
    "siglum_s",
    "shelfmark_s",
    "iiif_manifest_uris_sm",
]


def subdivision_size(req) -> int:
    size = req.app.ctx.config.get("iiif", {}).get("subdivision_size", 250)
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ValueError("iiif.subdivision_size must be a positive integer")
    return size


def selection(
    material: str | None = None, institution_id: str | None = None
) -> list[str]:
    """Select eligible holdings, optionally restricted by material/institution."""
    if material is not None and material not in MATERIALS:
        raise NotFound("Unknown IIIF material collection")
    filters = [
        "type:holding",
        "iiif_manifest_uris_sm:*",
        "-project_s:*",
        "institution_id:*",
    ]
    if material == "prints":
        filters.append("source_type_s:printed")
    elif material == "manuscripts":
        filters.append("source_type_s:manuscript")
    elif material == "other":
        # The negative clause also includes absent or newly introduced types.
        filters.append("-source_type_s:(printed OR manuscript)")
    if institution_id is not None:
        filters.append(f"institution_id:{json.dumps(f'institution_{institution_id}')}")
    return filters


def check_complete(result) -> bool:
    header = result.raw_response.get("responseHeader", {})
    return header.get("partialResults") in (None, False, "false")


async def documents(filters: list[str], fields: list[str]) -> AsyncIterator[dict]:
    """Use small-asc cursor traversal, rejecting partial or incomplete results."""
    result = await SolrConnection.search(
        {
            "query": "*:*",
            "filter": filters,
            "fields": fields,
            "limit": QUERY_PAGE_SIZE,
        },
        cursor=True,
    )
    # small-asc supplies the stable `id asc` sort for cursor queries.
    expected = result.hits
    retrieved = 0
    if not check_complete(result):
        raise SolrError("Solr returned partial IIIF results")

    async for doc in result:
        # Results.raw_response advances with small-asc's current cursor page.
        if not check_complete(result):
            raise SolrError("Solr returned partial IIIF results")
        retrieved += 1
        yield doc

    if not check_complete(result):
        raise SolrError("Solr returned partial IIIF results")

    if retrieved < expected:
        raise SolrError("Incomplete IIIF cursor traversal")


async def institution_directory(
    institution_id: str | None = None,
) -> tuple[dict[str, set[str]], dict[str, dict]]:
    """Collect membership and embedded institution labels in a single query."""
    result = await SolrConnection.search(
        {
            "query": "*:*",
            "filter": selection(institution_id=institution_id),
            "limit": 0,
            "facet": {
                "institutions": {
                    "type": "terms",
                    "field": "institution_id",
                    "limit": -1,
                    "mincount": 1,
                    "sort": "index asc",
                    "facet": {
                        **{
                            field: {
                                "type": "terms",
                                "field": field,
                                "limit": 1,
                                "sort": "index asc",
                            }
                            for field in ("institution_name_s", "city_s", "siglum_s")
                        },
                        "materials": {
                            "type": "terms",
                            "field": "source_type_s",
                            "limit": -1,
                            "mincount": 1,
                            "missing": True,
                        },
                    },
                }
            },
        }
    )
    if not check_complete(result):
        raise SolrError("Solr returned partial IIIF results")
    if result.hits == 0:
        # Solr omits JSON facet buckets entirely for an empty domain.
        return {}, {}

    memberships: dict[str, set[str]] = {}
    labels: dict[str, dict] = {}
    for bucket in result.raw_response["facets"]["institutions"]["buckets"]:
        ident = bucket["val"].removeprefix("institution_")
        types = bucket["materials"]
        memberships[ident] = {
            {"printed": "prints", "manuscript": "manuscripts"}.get(term["val"], "other")
            for term in types["buckets"]
        }
        if types.get("missing", {}).get("count", 0):
            memberships[ident].add("other")
        embedded = {
            field: bucket[field]["buckets"][0]["val"]
            for field in ("institution_name_s", "city_s", "siglum_s")
            if bucket.get(field, {}).get("buckets")
        }
        labels[ident] = {
            "none": [
                format_institution_label(embedded)
                if embedded.get("institution_name_s")
                else embedded.get("siglum_s") or f"RISM institution {ident}"
            ]
        }
    return memberships, labels


def root_reference(req) -> dict:
    return {
        "id": get_identifier(req, "iiif.root").rstrip("/") + "/",
        "type": "Collection",
        "label": {"en": ["RISM Online IIIF collections"]},
    }


def institution_reference(req, institution_id: str, label: dict) -> dict:
    return {
        "id": get_identifier(
            req, "iiif.institution", institution_id=institution_id
        ).rstrip("/")
        + "/",
        "type": "Collection",
        "label": label,
    }


def material_reference(req, institution_id: str, material: str) -> dict:
    return {
        "id": get_identifier(
            req,
            "iiif.material_collection",
            institution_id=institution_id,
            material=material,
        ).rstrip("/")
        + "/",
        "type": "Collection",
        "label": req.ctx.translations[MATERIAL_LABEL_KEYS[material]],
    }


def subdivision_reference(
    req, institution_id: str, material: str, page: int, total: int
) -> dict:
    size = subdivision_size(req)
    start = (page - 1) * size + 1
    end = min(page * size, total)
    parent = material_reference(req, institution_id, material)
    return {
        "id": get_identifier(
            req,
            "iiif.subdivision",
            institution_id=institution_id,
            material=material,
            page=str(page),
        ).rstrip("/")
        + "/",
        "type": "Collection",
        "label": {
            lang: [f"{value} {start}–{end}" for value in values]
            for lang, values in parent["label"].items()
        },
    }


def collection(reference: dict, items: list[dict], parent: dict | None = None) -> dict:
    result = {"@context": IIIF_CONTEXT, **reference, "items": items}
    if parent:
        result["partOf"] = [parent]
    return result


def manifest_label(doc: dict, translations: dict) -> dict:
    titles = deepcopy(doc.get("standard_titles_json") or [])
    if not titles:
        logger.warning("Missing IIIF title components: %s", doc["id"])
        titles = [{"title": doc.get("main_title_s") or doc["id"]}]
    for title in titles:
        if not title.get("title"):
            title["title"] = doc.get("main_title_s") or doc["id"]
        if not title.get("holding_siglum") and doc.get("siglum_s"):
            title["holding_siglum"] = doc["siglum_s"]
        if not title.get("holding_shelfmark"):
            title["holding_shelfmark"] = doc.get("shelfmark_s") or doc["id"]
    label = format_source_label(titles, translations)
    return label or {"none": [doc["id"]]}


async def manifest_references(req, institution_id: str, material: str) -> list[dict]:
    references = []
    seen: set[str] = set()
    async for doc in documents(selection(material, institution_id), MANIFEST_FIELDS):
        label = manifest_label(doc, req.ctx.translations)
        uris = doc.get("iiif_manifest_uris_sm", [])
        if not isinstance(uris, list) or any(
            not isinstance(uri, str) or not uri for uri in uris
        ):
            raise SolrError(f"Malformed IIIF references on {doc['id']}")
        # Deduplicate the whole branch before subdivision. The first holding in
        # id order supplies the label; URLs are not normalized or fetched.
        for uri in uris:
            if uri not in seen:
                seen.add(uri)
                references.append({"id": uri, "type": "Manifest", "label": label})
    return references


async def build_root(req) -> dict:
    memberships, labels = await institution_directory()
    ids = sorted(
        memberships, key=lambda ident: (next(iter(labels[ident].values()))[0], ident)
    )
    return collection(
        root_reference(req),
        [institution_reference(req, ident, labels[ident]) for ident in ids],
    )


async def build_institution(req, institution_id: str) -> dict:
    memberships, labels = await institution_directory(institution_id)
    if institution_id not in memberships:
        raise NotFound("Unknown or empty IIIF institution collection")
    result = collection(
        institution_reference(req, institution_id, labels[institution_id]),
        [
            material_reference(req, institution_id, material)
            for material in MATERIALS
            if material in memberships[institution_id]
        ],
        root_reference(req),
    )
    result["homepage"] = [
        {
            "id": get_identifier(
                req, "institutions.institution", institution_id=institution_id
            ),
            "type": "Text",
            "label": labels[institution_id],
            "format": "text/html",
        }
    ]
    return result


async def build_material(
    req, institution_id: str, material: str, page: str | None = None
) -> dict:
    if material not in MATERIALS:
        raise NotFound("Unknown IIIF material collection")
    number = None
    if page is not None:
        try:
            number = int(page)
        except ValueError:
            raise NotFound("Unknown IIIF subdivision") from None
        if number < 1 or page != str(number):
            raise NotFound("Unknown IIIF subdivision")
    references = await manifest_references(req, institution_id, material)
    if not references:
        raise NotFound("Unknown or empty IIIF material collection")
    total = len(references)
    size = subdivision_size(req)
    parent = material_reference(req, institution_id, material)
    if number is not None:
        if total <= size or (number - 1) * size >= total:
            raise NotFound("Unknown IIIF subdivision")
        return collection(
            subdivision_reference(req, institution_id, material, number, total),
            references[(number - 1) * size : number * size],
            parent,
        )
    _, labels = await institution_directory(institution_id)
    items = references
    if total > size:
        items = [
            subdivision_reference(req, institution_id, material, number, total)
            for number in range(1, (total + size - 1) // size + 1)
        ]
    return collection(
        parent,
        items,
        institution_reference(req, institution_id, labels[institution_id]),
    )
