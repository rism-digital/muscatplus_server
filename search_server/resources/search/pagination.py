import logging
import math
from typing import Optional, Dict

import pysolr
import serpy

from search_server.exceptions import PaginationParseException
from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.urls import replace_query_param, remove_query_param

log = logging.getLogger(__name__)

PAGE_QUERY_PARAM = "page"
ROWS_QUERY_PARAM = "rows"


class Pagination(ContextDictSerializer):
    """
    The PaginationSerializer will return a list of pagination links to assist
    consuming applications with navigation of the results. It is created as a
    Serializer because some keys will return None, and will thus be excluded from
    the output (see the comments in the ContextDictSerializer implementation for
    details.)
    """

    pagination_type = StaticField(
        label="type",
        value="PartialCollectionView"
    )
    first = serpy.MethodField()
    next = serpy.MethodField()
    previous = serpy.MethodField()
    last = serpy.MethodField()
    total_pages = serpy.MethodField(
        label="totalPages"
    )

    def _number_of_pages(self, total: int) -> int:
        """
        Shared method to get the total number of pages
        If there are more results than the size of the page, then
        there are more pages; otherwise, there is only one page.

        NB: This is true even if there are zero results for a query!

        This is also the page number for the last page if there is one, as the first page is 1, not 0
        :param total: The total number of results
        :return: the total number of pages
        """
        # Since we start counting pages at page 1, then we'll want to
        # `math.ceil` the value to get the total number of pages; e.g.:
        #  if 22 results and 20 rows, then 2 pages (22 / 20) = ceil(1.1) = 2
        # If the number of results are zero, or are less than the total on a results page
        # , then the first and last pages are the same
        #  if 19 results and 20 rows, then 1 page (19 / 20) = ceil(0.95) = 1
        #  if 0 results and 20 rows, then 1 page (0 / 20) = ceil(0) = 0 == 1 (with no results).

        req = self.context.get("request")
        rows: int = parse_row_number_from_request(req)
        pages: int = int(math.ceil(total / rows))
        # we always have at least 1 page, even if there are zero results
        return max(1, pages)

    def get_total_pages(self, obj: pysolr.Results) -> int:
        """
        :param obj: A pysolr Results object
        :return: the total number of pages
        """
        return self._number_of_pages(obj.hits)

    def get_first(self, total_results: int) -> str:  # noqa
        """
        The first page of results. In the current implementation, this corresponds to the
        query string without a `page` query parameter, so this will return the full query
        string with the `page` parameter removed. This is always present in the response.

        :param total_results: The total number of results
        :return: The URL to the first page.
        """
        req = self.context.get("request")
        # Vary the query dictionary for the first result page
        return remove_query_param(req.url, PAGE_QUERY_PARAM)

    def get_next(self, obj: pysolr.Results) -> Optional[str]:
        """
        Pretty self-explanatory. Gets the URL for the next page of results.
        The only corner case is that it will return None if the next page is
        calculated to be beyond the edge of all pages.

        :param obj: A pysolr.Results object
        :return: The URL to the next page, or None if it is beyond the end of all pages.
        """
        req = self.context.get("request")

        this_page: int = parse_page_number_from_request(req)
        next_page: int = this_page + 1

        last_page: int = self._number_of_pages(obj.hits)

        # if the next page is beyond the total number of pages, return
        # None, which will omit it from the response.
        if next_page > last_page:
            return None

        return replace_query_param(req.url, PAGE_QUERY_PARAM, next_page)

    def get_previous(self, obj: pysolr.Results) -> Optional[str]:  # noqa
        """
        Gets the link to the previous page. An important comment is inlined below
        to explain a particular edge-case and why it is that way.

        :param obj: The total number of results
        :return: The URL to the previous page, or None if it is on the first page.
        """
        req = self.context.get("request")
        url: str = req.url

        this_page: int = parse_page_number_from_request(req)

        prev_qdict = req.args.copy()
        prev_page: int = this_page - 1

        # if the previous page is lower than 1 (i.e., the first page)
        # then there is no previous page, and we should not provide
        # the ability to navigate to it.
        if prev_page < 1:
            return None

        # A corner case. We represent the first page as a URI without a 'page'
        # query parameter. For consistency with the `first` parameter (see above),
        # if the previous page is also the first page, we remove the `page` parameter from
        # the query string; otherwise we set it to the appropriate value.
        if prev_page == 1 and PAGE_QUERY_PARAM in prev_qdict:
            return remove_query_param(url, PAGE_QUERY_PARAM)

        return replace_query_param(url, PAGE_QUERY_PARAM, prev_page)

    def get_last(self, obj: pysolr.Results) -> Optional[str]:
        """
        Gets the last page of results. If there is only one page, then this will not
        be included in the pagination result.

        :param obj: a pysolr Results object
        :return: The URL to the next page, or None if the last page is also the first page.
        """
        last_page: int = self._number_of_pages(obj.hits)

        # Show the last page link only if there is more than one page
        # If the number of results are zero, or are less than the total on a results page
        # , then the first and last pages are the same and the number of pages is 1, so we will not show the 'last_page'
        # link
        if last_page <= 1:
            return None

        req = self.context.get("request")

        return replace_query_param(req.url, PAGE_QUERY_PARAM, last_page)


def parse_row_number_from_request(req) -> int:
    """
    Parses the row parameter from the request. If it's None, return the default rows
    Any invalid cases (rows not in the permitted list, rows not an int etc.) will raise a PaginationParseError

    :param req:
    :return: the number of rows (i.e. the page size)
    """
    this_page_qstr: Optional[str] = req.args.get(ROWS_QUERY_PARAM, None)

    return parse_row_number(req, this_page_qstr)


def parse_row_number(req, row_query_string: Optional[str]) -> int:
    """
    Parses the row parameter string. If it's None, return the default rows
    Any invalid cases (rows not in the permitted list, rows not an int etc.) will raise a PaginationParseError
    :param req: A Sanic request instance
    :param row_query_string: The query string.
    :return: the number of rows (i.e. the page size)
    """
    rows: int
    search_config: Dict = req.app.config["search"]

    if not row_query_string:
        return search_config['rows']

    try:
        rows: int = int(row_query_string)
    except ValueError as e:
        raise PaginationParseException("Invalid value for rows. If provided, it must be a whole number.")

    if rows not in search_config['page_sizes']:
        raise PaginationParseException(f"Invalid value for page size. Only {', '.join([str(v) for v in search_config['page_sizes']])} are acceptable values")

    return rows


def parse_page_number_from_request(req) -> int:
    """
    Parses the page parameter from the request. If it doesn't exist, return 1
    Any invalid cases (page < 1, page not an int etc.) will raise a PaginationParseError

    :param req:
    :return: the current page number parsed from the request
    """
    this_page_qstr: str = req.args.get(PAGE_QUERY_PARAM, None)
    return parse_page_number(this_page_qstr)


def parse_page_number(page_query_string: Optional[str]) -> int:
    """
    Parses the page string. If it's None, return 1
    Any invalid cases (page < 1, page not an int etc.) will raise a PaginationParseError
    :param page_query_string:
    :return: the current page number
    """
    # Set this page to 1 (first page) if the page qstring is not set.
    if not page_query_string:
        return 1

    try:
        this_page: int = int(page_query_string)
    except ValueError as e:
        raise PaginationParseException("Page number must be an integer")
    if this_page < 1:
        raise PaginationParseException("Page number must be greater than 0")

    return this_page
