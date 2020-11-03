from typing import Dict, Optional

from search_server.exceptions import InvalidQueryException, PaginationParseException
from search_server.resources.search.pagination import parse_page_number, parse_row_number

import logging

log = logging.getLogger(__name__)


class SearchRequest:
    def __init__(self, req):
        self._req = req
        # If there is no q parameter it will return all results
        self._requested_query: str = req.args.get("q", "*:*")

        self._page: Optional[str] = req.args.get("page", None)
        self._return_rows: Optional[str] = req.args.get("rows", None)

    def compile(self) -> Dict:
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
            "rows": return_rows
        }
