import math
from collections.abc import Generator
from typing import Union, Optional, TypedDict

import httpx
import orjson

import logging
log = logging.getLogger(__name__)


class SolrError(Exception):
    pass


class JsonAPIRequest(TypedDict, total=False):
    """
    A JSON API Request can be typed when it is being sent to the .search() method. This provides
    a handy way of ensuring that the keys in the request dictionary
    """
    query: str
    filter: Union[str, list[str]]
    params: dict
    offset: int  # aka 'start'
    limit: int   # aka 'rows'
    sort: str
    fields: list[str]
    facet: list[dict]


class JSONTermsSuggestRequest(TypedDict, total=False):
    query: str
    fields: list[str]


class Results:
    """
    Originally based on the pysolr Request object, but with some changes in behaviour to support more natural
    cursor iteration.

    """
    __slots__ = ("raw_response", "current_page", "num_pages", "docs", "hits", "debug", "highlighting", "facets",
                 "spellcheck", "stats", "qtime", "grouped", "nextCursorMark", "_query_url", "_query", "_is_cursor",
                 "_idx", "_page_idx")

    def __init__(self, result_json: dict, url: Optional[str] = None, query: Optional[JsonAPIRequest] = None) -> None:
        self.raw_response: dict = result_json
        self.__set_instance_values(result_json)

        # parameters supporting cursor-based results
        self._query_url: Optional[str] = url
        self._query: Optional[JsonAPIRequest] = query

        # condense the check into a single boolean. If this is a cursor query, then the original URL and the
        # original query dictionary are passed into the results so that we can re-execute the search for the next
        # page of results; if not, then only the result dictionary is sent.
        self._is_cursor: bool = all((self._query_url, self._query))
        # These are for iterating documents
        self._idx: int = 0
        self._page_idx: int = 0

    def __set_instance_values(self, raw_response: dict) -> None:
        response_part: dict = raw_response.get("response", {})
        self.docs: list = response_part.get("docs", [])
        self.hits: int = response_part.get("numFound", 0)

        # other response metadata
        self.debug: dict = raw_response.get("debug", {})
        self.highlighting: dict = raw_response.get("highlighting", {})
        self.facets: dict = raw_response.get("facet_counts", {})
        self.spellcheck: dict = raw_response.get("spellcheck", {})
        self.stats: dict = raw_response.get("stats", {})
        self.qtime: Optional[str] = raw_response.get("responseHeader", {}).get("QTime", None)
        self.grouped: dict = raw_response.get("grouped", {})

        self.nextCursorMark: Optional[str] = raw_response.get("nextCursorMark", None)

        # These are for iterating pages
        self.current_page: int = 1

        # Assume the length of the first page is the length of all the pages
        _docslen: int = len(self.docs)
        # avoid divide-by-zero for no results
        # we always have at least 1 page, even if there are zero results
        _rows: int = _docslen if _docslen > 0 else 1
        self.num_pages: int = int(math.ceil(self.hits / _rows))

    def __len__(self):
        if self._is_cursor:
            return self.hits
        else:
            return len(self.docs)

    async def nextpage(self) -> bool:
        """
        Manually advances the results to the next page. This depends on the initial request being called with
        `cursor=True`, but rather than iterating through the results and automatically going to the next page,
        this allows for iterating through a page of results and then manually advancing to the next page before
        iterating through the next page of results. This is useful for chunking up large pages of results for
        processing while still using the cursor capability.

        res = client.search(...)

        for i in range(res.num_pages):
            # do something with res.docs for this page

            # advance to the next page for the next iteration.
            res.nextpage()

        NB: For this to work it needs to be run with `cursor=True` on the initial request.
        """
        if self.current_page < self.num_pages:
            self._query.get("params", {}).update({
                "cursorMark": self.nextCursorMark
            })
            self.raw_response = await _post_data_to_solr(self._query_url, self._query)
            self.__set_instance_values(self.raw_response)
            self.current_page += 1
            return True

        return False

    async def __aiter__(self) -> Generator:
        if self._is_cursor is False:
            yield self.docs[self._page_idx]
        else:
            while self._idx < self.hits:
                try:
                    yield self.docs[self._page_idx]  # type: ignore
                except IndexError:
                    self._page_idx = 0
                    # update the cursormark with the cursor mark from the previous query.
                    self._query.get("params", {}).update({
                        "cursorMark": self.nextCursorMark
                    })
                    self.raw_response = await _post_data_to_solr(self._query_url, self._query)
                    self.__set_instance_values(self.raw_response)
                    self.current_page += 1

                    if self.docs:
                        yield self.docs[self._page_idx]
                    else:
                        break

                self._page_idx += 1
                self._idx += 1


class Solr:
    """
    A custom-built Solr library that uses JSON exclusively to communicate with Solr.

    For searches and gets, uses the JSON Request API to fetch results.

    Passes the JSON docs to Solr directly for updates.

    Uses the HTTPX library.
    """
    __slots__ = ("_url",)

    def __init__(self, url: str) -> None:
        self._url: str = url

    async def search(self, query: JsonAPIRequest, cursor: bool = False, handler: str = "/select") -> Results:
        """
        Consumes a Solr JSON Request API configuration.

        The 'cursor' parameter, False by default, determines the behaviour of the Results. If it is false,
        iterating over the results will return only the list of rows returned in a paginated query, and retrieving
        subsequent pages must be done with the 'offset' (start) and 'limit' (rows) parameters.

        If 'cursor' is true, then iterating over the results will cause the results class to automatically retrieve
        the next page, so that the full list of results can be returned simply by doing 'for doc in results'....

        :param query: A dictionary corresponding to a Solr JSON Request API configuration for a query
        :param cursor: A boolean that determines whether a cursor is used in the search results.
        :param handler: A Solr handler endpoint to target the query
        :return:
        """
        url: str = self._create_url(handler)

        if cursor:
            if 'offset' in query or 'start' in query.get("params", {}):
                raise SolrError("Offset or start is not supported when performing a cursor query.")

            # 'legacy' solr query parameters can be stored in the 'params' key. Ensure we have one
            # if it's not already passed in.
            if 'params' not in query:
                query['params'] = {}

            query['params'].update({
                "cursorMark": "*"
            })

            # cursor queries need to be explicitly sorted, which makes them not very useful
            # for doing relevance search, but very good for retrieving all records of a given ID.
            # We just need to ensure that a unique field (typically 'id') is present in the Solr
            # sorting statement. NB: We're still inside the 'if cursor' block, so this will only be
            # run if we are in a cursor statement!
            if 'sort' not in query and 'sort' not in query.get("params", {}):
                query.update({"sort": "id asc"})
            # The leading space is significant! We want to make sure we have a standalone `id` field name,
            # otherwise statements like `foo_id asc` would match here.
            elif 'sort' in query and " id asc" not in query["sort"]:
                query["sort"] = f"{query['sort']}, id asc"
            else:
                raise SolrError("Could not determine a sort parameter when performing a cursor query.")

        search_results: dict = await _post_data_to_solr(url, query)

        if cursor:
            return Results(search_results, url, query)

        return Results(search_results)

    async def add(self, docs: list[dict], handler: str = "/update") -> dict:
        url: str = self._create_url(handler)
        return await _post_data_to_solr(url, docs)

    async def get(self, docid: str, fields: Optional[list[str]] = None, handler: str = "/get") -> Optional[dict]:
        """
        Sends a request to the Solr RealtimeGetHandler endpoint to fetch a single
         record by its ID. Special consideration must be made to package up the
         request in the JSON Request API using the 'params' block.

        :param docid: A document ID
        :param fields: An optional list of fields to return. `None` will return all fields.
        :param handler: The request handler. Defaults to '/get'
        :return: A dictionary containing the Solr document.
        """
        url: str = self._create_url(handler)
        qdoc: dict = {"params": {"id": docid}}

        if fields and isinstance(fields, list):
            qdoc.update({"fields": fields})

        doc: dict = await _post_data_to_solr(url, qdoc)

        return doc.get("doc") or None

    async def delete(self, query: str, handler: str = "/update") -> Optional[dict]:
        base_url: str = self._create_url(handler)
        # automatically commit the result of the delete query so we don't have
        # old docs hanging around.
        delete_url: str = f"{base_url}?commit=true"
        res: dict = await _post_data_to_solr(delete_url, {"delete": {"query": query}})

        return res

    async def term_suggest(self, query: JSONTermsSuggestRequest, handler: str = "/terms") -> Optional[dict]:
        """
        Uses the Solr terms handler to provide a suggester. Requires that both the 'fields' and 'query'
        parameters are provided, e.g.,

        t: dict = term_suggest({"query": "Moza", "fields": ["creator_name_s"]})

        This will apply a regex query of ".*Moza.*" to the query, meaning it will find the top 10 entries, by
        document count, for a term matching this pattern.

        :param query: A JSONTermsSuggestRequest-compliant dictionary (required)
        :param handler: An optional Solr handler for switching the handlers.
        :return: A dictionary containing the Solr response
        """
        base_url: str = self._create_url(handler)
        solr_query: dict = {"params": {
            "omitHeader": "true",
            "terms": "true",
            "terms.fl": query["fields"],
            "terms.regex": f".*{query['query']}.*",
            "terms.regex.flag": ["case_insensitive",
                                 "canon_eq",
                                 "unicode_case"]
            }
        }

        return await _post_data_to_solr(base_url, solr_query)

    def _create_url(self, handler: str) -> str:
        return "/".join([self._url.rstrip("/"), handler.lstrip("/")])


async def _post_data_to_solr(url: str, data: Union[list, dict]) -> dict:
    headers: dict = {
        "Accept-Encoding": "gzip",
        "Content-Type": 'application/json'
    }

    async with httpx.AsyncClient(timeout=None, headers=headers) as client:
        try:
            res = await client.post(url, content=orjson.dumps(data))

        except httpx.TimeoutException as err:
            error_message: str = "Connection to server %s timed out: %s"
            raise SolrError(error_message % (url, err))
        except httpx.ConnectError as err:
            error_message: str = "Failed to connect to server at %s: %s"
            raise SolrError(error_message % (url, err))
        except httpx.HTTPError as err:
            error_message: str = "Unhandled connection error for %s: %s"
            raise SolrError(error_message % (url, err))

        if res.status_code != 200:
            error_message: str = "Solr responded with HTTP Error %s: %s"
            raise SolrError(error_message % (res.status_code, res.reason_phrase))

        log.debug("Upstream Request took %s s for %s", res.elapsed.total_seconds(), url)
        json_result: dict = orjson.loads(res.text)

    return json_result
