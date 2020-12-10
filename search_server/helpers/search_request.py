from typing import Dict, Optional, List

from search_server.exceptions import InvalidQueryException, PaginationParseException
from search_server.resources.search.pagination import parse_page_number, parse_row_number

import logging

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
    def __init__(self, req):
        self._req = req
        self.filters: List = []
        # If there is no q parameter it will return all results
        self._requested_query: str = req.args.get("q", "*:*")
        self._page: Optional[str] = req.args.get("page", None)
        self._return_rows: Optional[str] = req.args.get("rows", None)

    def compile(self) -> Dict:
        filters: List = self.filters

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
            "start": start_row,
            "rows": return_rows,
            "fq": filters
        }
