import logging
import re
from typing import Optional
from urllib.parse import unquote

from small_asc.client import Results

from search_server.resources.search.pagination import parse_page_number
from search_server.resources.search.search_results import SearchResults
from shared_helpers.identifiers import ID_SUB
from shared_helpers.solr_connection import SolrConnection

log = logging.getLogger("mp_export")

INVALID_SIGLUM = re.compile(r"^[\w-]+$")


async def handle_institution_sigla_request(req, siglum: str) -> Optional[str]:
    incoming_sig: str = unquote(siglum)

    # \w in the pattern matches the underscore, which we don't want to match here.
    # If the regex doesn't match the return value will be None, in which case it's
    # a problematic siglum.
    if "_" in incoming_sig or re.fullmatch(INVALID_SIGLUM, incoming_sig) is None:
        log.warning(
            "Invalid characters in siglum, so it cannot match anything: %s",
            incoming_sig,
        )
        return None

    # ensure characters are handled as UTF-8 using the 'unquote' method.
    fq: list = ["type:institution", f"siglum_s:{incoming_sig}"]
    institution_record: Results = await SolrConnection.search(
        {"query": "*:*", "filter": fq, "fields": ["id"]}, handler="/query"
    )

    if institution_record.hits == 0:
        return None

    if institution_record.hits > 1:
        log.warning(
            "More than one result was returned for siglum %s. This shouldn't happen.",
            siglum,
        )

    institution_record_id: str = institution_record.docs[0]["id"]
    institution_id = re.sub(ID_SUB, "", institution_record_id)

    return f"/institutions/{institution_id}"


async def handle_siglum_search_request(req) -> Optional[dict]:
    # query types:
    #  - all: Any field
    #  - name: Library name
    #  - siglum: Library siglum
    #  - city: City
    #  - country: Country
    #  q = query
    #  qt = query type, keyword search over the whole record if omitted.
    #  page = control pagination
    query: Optional[str] = req.args.get("q", None)
    query_type: Optional[str] = req.args.get("qt", "all")
    page: Optional[str] = req.args.get("page", None)

    page_num: int = parse_page_number(page)
    rows: int = 20

    start_row: int = 0 if page_num == 1 else ((page_num - 1) * rows)

    if not query:
        return None

    query_solr_fields: dict[str, str] = {
        "name": "names_ft",
        "siglum": "siglum_s",
        "city": "city_ft",
        "country": "country_names_ft",
        "all": "",
    }

    if query_type not in query_solr_fields:
        return None

    fq: list[str] = ["type:institution", "!project_s:*", "has_siglum_b:true"]

    query_field: str = query_solr_fields[query_type]
    if query_type == "all":
        solr_query = f"{query}"
    elif query_type == "siglum":
        # We need to do strict left-edge matching, which we can get if we do a regex search.
        solr_query = f"{query_field}:/{query}.*/"
    else:
        solr_query = f"{query_field}:{query}"

    solr_query_obj = {
        "query": solr_query,
        "filter": fq,
        "offset": start_row,
        "limit": rows,
        "sort": "score desc",
        "params": {"boost": ["scale(field(total_sources_i), 1, 100)"]},
    }

    results: Results = await SolrConnection.search(
        solr_query_obj, handler="/siglaQuery"
    )
    search_res: dict = await SearchResults(results, context={"request": req}).data

    return search_res
