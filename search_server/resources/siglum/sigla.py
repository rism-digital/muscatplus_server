import re
from urllib.parse import unquote

from sanic.log import logger
from small_asc.client import JsonAPIRequest, Results

from search_server.helpers.identifiers import strip_prefix
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.pagination import parse_page_number
from search_server.resources.search.search_results import SearchResults

INVALID_SIGLUM = re.compile(r"^[\w-]+$")


async def handle_institution_sigla_request(req, siglum: str) -> str | None:
    incoming_sig: str = unquote(siglum)

    # \w in the pattern matches the underscore, which we don't want to match here.
    # If the regex doesn't match, the return value will be None, in which case it's
    # a problematic siglum.
    if "_" in incoming_sig or re.fullmatch(INVALID_SIGLUM, incoming_sig) is None:
        logger.warning(
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
        logger.warning(
            "More than one result was returned for siglum %s. This shouldn't happen.",
            siglum,
        )

    institution_record_id: str = institution_record.docs[0]["id"]
    institution_id = strip_prefix(institution_record_id)

    return f"/institutions/{institution_id}"


async def handle_siglum_search_request(req) -> dict | None:
    # query types:
    #  - all: Any field
    #  - name: Library name
    #  - siglum: Library siglum
    #  - city: City
    #  - country: Country
    #  q = query
    #  qt = query type, keyword search over the whole record if omitted.
    #  page = control pagination
    query: str | None = req.args.get("q", None)
    query_type: str | None = req.args.get("qt", "all")
    page: str | None = req.args.get("page", None)

    page_num: int = parse_page_number(page)
    rows: int = 20

    start_row: int = 0 if page_num == 1 else ((page_num - 1) * rows)

    if not query:
        return None

    query_solr_fields: dict[str, str] = {
        "name": "name_al",
        "siglum": "siglum_kwf",  # This is case-sensitive but folding
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
        # We need to do left-edge matching, so add a wildcard at the end.
        solr_query = f"{query_field}:{query}*"
    else:
        solr_query = f"{query_field}:{query}"

    solr_query_obj: JsonAPIRequest = {
        "query": solr_query,
        "filter": fq,
        "offset": start_row,
        "limit": rows,
        "sort": "score desc"
    }

    results: Results = await SolrConnection.search(
        solr_query_obj, handler="/siglaQuery"
    )
    search_res: dict = await SearchResults(results, context={"request": req}).serialized

    return search_res
