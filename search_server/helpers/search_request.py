from typing import Dict, Optional, List

from search_server.exceptions import InvalidQueryException, PaginationParseException
from search_server.resources.search.pagination import parse_page_number, parse_row_number
import urllib.parse
import logging

import ujson

log = logging.getLogger(__name__)


class SearchRequest:
    """
    Takes a number of parameters passed in from a search request and compiles them to produce a set of
    parameters that can then be sent off to Solr. This is useful as a place to contain all the logic for
    how requests from the front-end get parsed and compiled to a valid Solr request, particularly around
    handling pagination.

    While it's primary function is to interact with Solr for the main search interface, it can also be used
    in other places where paginated interactions with Solr are required, such as viewing a person's list of
    related sources.
    """
    default_sort = "id asc"

    def __init__(self, req, sort: Optional[str] = None):
        self._req = req
        self._app_config = req.app.config
        self.filters: List = []
        # If there is no q parameter it will return all results
        self._requested_query: str = req.args.get("q", "*:*")
        self._page: Optional[str] = req.args.get("page", None)
        self._return_rows: Optional[str] = req.args.get("rows", None)
        self.sorts: List = []
        self._alias_map = {f"{cnf['alias']}": f"{solr_f}" for solr_f, cnf in self._app_config["search"]["facet_fields"].items()}

    def _get_requested_filters(self) -> List:
        fqs: List = self._req.args.getlist("fq")
        if not fqs:
            return []

        requested_filters: List = []

        for filt in fqs:
            # split the incoming filters
            field, raw_value = filt.split(":")
            # Map them to the actual solr fields
            # Ignore any parameters not explicitly configured
            if field not in self._alias_map:
                continue

            # do some processing and normalization on the value. First ensure we have a non-entity string.
            # This should convert the URL-encoded parameters back to 'normal' characters
            unencoded_value: str = urllib.parse.unquote_plus(raw_value)

            # Then remove any quotes (single or double)
            value: str = unencoded_value.replace("\"", "").replace("'", "")

            # Finally, ensure that we *always* pass it to Solr as a quoted value. (The single quotes here will
            # get converted to double-quotes by the internals of the API).
            new_val = f"{self._alias_map[field]}:\"{value}\""
            requested_filters.append(new_val)

        return requested_filters

    def _get_facets(self) -> str:
        # This uses the alias feature for facets to map our 'public' name for the facet
        # to the actual solr field name being used. This means that in the output of this
        # (that is, when the search request is returned) the facets will be available by
        # the alias, not by the solr field name as would be normally expected.
        facet_cfg: Dict = self._app_config["search"]["facet_fields"]
        json_facets: Dict = {}

        for solr_field, field_cfg in facet_cfg.items():
            field_alias = field_cfg["alias"]

            json_facets[field_alias] = {
                "type": "terms",
                "field": solr_field,
                "sort": f"{field_cfg['sort']}",
                "limit": 50
            }

        # Serialize the JSON to a string so that it can go over the Solr API.
        # PySolr will transparently 'do the right thing' with the request.
        return ujson.dumps(json_facets)

    def compile(self) -> Dict:
        filters: List = self.filters + self._get_requested_filters()

        if self._req.args.get("q"):
            sorts = ["score desc"]
        else:
            sorts = ["main_title_ans asc"]

        # If page is set, try to parse out the page number from the
        # value. If it's not a number, flag the request as invalid.
        try:
            page_num: int = parse_page_number(self._page)
        except PaginationParseException:
            raise InvalidQueryException("Invalid value for page. If provided, it must be a whole number greater than 1.")

        try:
            return_rows: int = parse_row_number(self._req, self._return_rows)
        except PaginationParseException:
            raise InvalidQueryException("Invalid value for rows.")

        start_row: int = 0 if page_num == 1 else ((page_num - 1) * return_rows)

        return {
            "q": [self._requested_query],
            "fq": filters,
            "start": start_row,
            "rows": return_rows,
            "sort": ", ".join(sorts),
            "json.facet": self._get_facets()
        }
