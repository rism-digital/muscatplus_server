from typing import Dict, Optional, List

from search_server.exceptions import InvalidQueryException, PaginationParseException
from search_server.resources.search.pagination import parse_page_number, parse_row_number
import urllib.parse
import logging

import ujson

log = logging.getLogger(__name__)


# Some helper functions to work with the field and filter configurations.
def filters_for_mode(cfg: Dict, mode: str) -> Dict:
    filter_configuration: Dict = cfg["search"]["filters"]
    filts: Optional[Dict] = filter_configuration.get(mode)
    return filts or {}


def field_alias_map(filters_config: Dict) -> Dict:
    return {f"{cnf['alias']}": f"{solr_f}" for solr_f, cnf in filters_config.items()}


def display_name_alias_map(filters_config: Dict) -> Dict:
    return {f"{cfg['alias']}": f"{cfg['display_name']}" for cfg in filters_config.values()}


def display_value_alias_map(filters_config: Dict) -> Dict:
    return {f"{cfg['alias']}": cfg['display_value_map'] for cfg in filters_config.values() if cfg.get('display_value_map')}


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
        self._app_config = req.app.ctx.config

        # Validate the incoming request to see if we can parse it.
        # This will raise an exception if there is anything wrong.
        self._validate_incoming_request()

        # Set up some public properties
        self.filters: List = []
        self.sorts: List = []

        # If there is no q parameter it will return all results
        self._requested_query: str = req.args.get("q", "*:*")
        self._requested_filters: List = req.args.getlist("fq", [])
        self._requested_mode: str = req.args.get("mode", self._app_config["search"]["default_mode"])
        self._page: Optional[str] = req.args.get("page", None)
        self._return_rows: Optional[str] = req.args.get("rows", None)

        self._filters_for_mode: Dict = filters_for_mode(self._app_config, self._requested_mode)
        self._alias_map: Dict = field_alias_map(self._filters_for_mode)

    def _validate_incoming_request(self) -> None:
        """
        Raises an InvalidQueryException with specific responses for different error conditions.
        Doing this once means we can assume that if it passes, we don't have to raise this exception
        elsewhere in the class.

        :return: None
        """
        valid_q_param: List = self._req.args.getlist("q", [])
        if len(valid_q_param) > 1:
            raise InvalidQueryException("Only one query parameter can be supplied.")

        requested_modes: List = self._req.args.getlist("mode", [])
        if len(requested_modes) > 1:
            raise InvalidQueryException("Only one mode parameter can be supplied.")

        modes: Dict = self._app_config["search"]["modes"]
        if len(requested_modes) == 1:
            requested_mode_config: Optional[Dict] = modes.get(requested_modes[0])

            # if the requested mode does not match anything configured, raise an exception
            if not requested_mode_config:
                raise InvalidQueryException("Invalid value for the requested mode.")

        try:
            _ = parse_page_number(self._req.args.get("page", None))
        except PaginationParseException as e:
            raise InvalidQueryException(e)

        try:
            _ = parse_row_number(self._req, self._req.args.get("rows", None))
        except PaginationParseException as e:
            raise InvalidQueryException(e)

    def _modes_to_filter(self) -> str:
        """
        Turns the incoming 'mode' request to a string suitable for use in a Solr `fq` query.

        :return: A string with the appropriate "OR" statements applied.
        """
        modes: Dict = self._app_config["search"]["modes"]
        mode_cfg: Dict = modes[self._requested_mode]
        record_types: List = mode_cfg["record_types"]
        solr_types_field: List = [f"type:{v}" for v in record_types]

        return " OR ".join(solr_types_field)

    def _compile_filters(self) -> List:
        filter_statements: List = []

        for filt in self._requested_filters:
            field, raw_value = filt.split(":")

            # do some processing and normalization on the value. First ensure we have a non-entity string.
            # This should convert the URL-encoded parameters back to 'normal' characters
            unencoded_value: str = urllib.parse.unquote_plus(raw_value)

            # Then remove any quotes (single or double)
            value: str = unencoded_value.replace("\"", "").replace("'", "")

            # Finally, ensure that we *always* pass it to Solr as a quoted value. (The single quotes here will
            # get converted to double-quotes by the internals of the pysolr API). We use the previously-constructed
            # alias map to map the public field name to the private solr field.
            new_val: str = f"{self._alias_map[field]}:\"{value}\""
            filter_statements.append(new_val)

        return filter_statements

    def _get_facets(self) -> str:
        # if there are no filter, return an empty string. This will cause Solr to not emit any facets through
        # the JSON Facet API
        if not self._filters_for_mode:
            return ""

        json_facets: Dict = {}

        for solr_field, field_cfg in self._filters_for_mode.items():
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
        mode_filter: str = self._modes_to_filter()
        self.filters.append(mode_filter)

        requested_filters: List = self._compile_filters()
        self.filters += requested_filters

        # These have already been checked in the validation, so they shouldn't raise an exception here.
        page_num: int = parse_page_number(self._page)
        return_rows: int = parse_row_number(self._req, self._return_rows)
        start_row: int = 0 if page_num == 1 else ((page_num - 1) * return_rows)

        return {
            "q": [self._requested_query],
            "fq": self.filters,
            "start": start_row,
            "rows": return_rows,
            # "sort": ", ".join(sorts),
            "json.facet": self._get_facets()
        }
