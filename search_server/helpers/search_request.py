import logging
import urllib.parse
from typing import Dict, Optional, List

from search_server.exceptions import InvalidQueryException, PaginationParseException
from search_server.resources.search.pagination import parse_page_number, parse_row_number

log = logging.getLogger(__name__)

# Some of the facets and filters need to have a solr `{!tag}` prepended. We'll
# define them up-front.
RANGE_FILTER_TAG: str = "RANGE_FILTER"
SELECTOR_FILTER_TAG: str = "SELECTOR_FILTER"
MODE_FILTER_TAG: str = "MODE_FILTER"


# Some helper functions to work with the field and filter configurations.
def filters_for_mode(cfg: Dict, mode: str) -> List:
    """
    Returns a set of facets to apply when a particular result mode is chosen.
    :param cfg: The application configuration
    :param mode: The selected mode
    :return: The list of filter fields from the configuration for a given mode, or an empty dictionary if no filters
        are configured.
    """
    filter_configuration: Dict = cfg["search"]["filters"]
    filts: List = filter_configuration.get(mode, [])
    return filts


def filter_type_map(filters_config: List) -> Dict:
    """
    A dictionary that maps the type of filter (toggle, selector, etc.) to the alias.
    :param filters_config:
    :return:
    """
    return {f"{cnf['alias']}": f"{cnf['type']}" for cnf in filters_config}


def filter_label_map(filters_config: List) -> Dict:
    return {f"{cnf['alias']}": f"{cnf['label']}" for cnf in filters_config}


def alias_config_map(filters_config: List) -> Dict:
    """
    A dictionary that maps the incoming API request 'alias' to the config block for that facet config.
    :param filters_config: A list of all the filters for the map

    :return:
    """
    return {f"{cnf['alias']}": cnf for cnf in filters_config}


def field_alias_map(filters_config: List) -> Dict:
    """
    A dictionary mapping the configured alias to the Solr field. Used for referencing the solr field using the
    alias.
    :param filters_config: The application configuration
    :return: A dictionary of values mapping the alias to the solr field.
    """
    return {f"{cnf['alias']}": f"{cnf['field']}" for cnf in filters_config}


class SearchRequest:
    """
    Takes a number of parameters passed in from a search request and compiles them to produce a set of
    parameters that can then be sent off to Solr. This is useful as a place to contain all the logic for
    how requests from the front-end get parsed and compiled to a valid Solr request, particularly around
    handling pagination.

    While it's primary function is to interact with Solr for the main search interface, it can also be used
    in other places where paginated interactions with Solr are required, such as viewing a person's list of
    related sources.

    A bit of terminology to be aware of:
        - FILTERS are requests sent to Solr to filter queries
        - FACETS are responses from Solr giving us the values for specific facet fields

    In other words: Values from FACETS are then used by the client to compose requests for FILTERS.

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

        # Configure the facets to show for the selected mode.
        self._facets_for_mode: List = filters_for_mode(self._app_config, self._requested_mode)
        self._alias_config_map: Dict = alias_config_map(self._facets_for_mode)

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

        :return: The alias mapping e.g., 'mode=people' to "type:person"
        """
        modes: Dict = self._app_config["search"]["modes"]
        mode_cfg: Dict = modes[self._requested_mode]
        record_type: str = mode_cfg["record_type"]

        return f"type:{record_type}"

    def _compile_filters(self) -> List:
        filter_statements: List = []

        for filt in self._requested_filters:
            field, raw_value = filt.split(":")

            # If the field we're looking at is not one that we know about,
            # ignore it and go to the next one.
            if field not in self._alias_config_map:
                continue

            filter_config: dict = self._alias_config_map[field]
            filter_type: str = filter_config['type']

            # do some processing and normalization on the value. First ensure we have a non-entity string.
            # This should convert the URL-encoded parameters back to 'normal' characters
            unencoded_value: str = urllib.parse.unquote_plus(raw_value)

            # Then remove any quotes (single or double)
            quoted_value: str = unencoded_value.replace("\"", "").replace("'", "")

            # Finally, ensure that we pass it to Solr as a quoted value if it is not a range search.
            # This is because Solr interprets spaces in an unquoted value to be an implicit "AND".
            #   - Range queries will not work when they are quoted.
            #   - Toggle queries only accept 'true' (or "True" or "TRUE") as a value, to indicate they are active. All
            #     other values provided will be ignored.
            #
            # We use the alias map to map the public API name to the
            # private solr field.
            value: str

            if filter_type == 'range':
                value = quoted_value
            elif filter_type == "toggle":
                # We only accept 'true' as a value for toggles; anything else will
                # cause us to ignore this filter request. We do, however, try it against
                # all possible case variants.
                if raw_value.lower() != "true":
                    continue

                value = filter_config['active_value']
            else:
                value = f"\"{quoted_value}\""

            new_val: str = f"{filter_config['alias']}:{value}"

            # Some field types need to be tagged to help modify their behaviour and interactions with
            # facets for multi-select faceting. See:
            # https://solr.apache.org/guide/8_8/faceting.html#tagging-and-excluding-filters
            if filter_type == "range":
                new_val = f"{{!tag={RANGE_FILTER_TAG}}}{new_val}"
            elif filter_type == "selector":
                new_val = f"{{!tag={SELECTOR_FILTER_TAG}}}{new_val}"

            filter_statements.append(new_val)

        return filter_statements

    def _get_facets(self) -> dict:
        # if there are no filter, return an empty string. This will cause Solr to not emit any facets through
        # the JSON Facet API
        json_facets: dict = {}
        # a list of all possible modes configured.
        all_modes: str = " OR ".join([f"type:{v['record_type']}" for k, v in self._app_config['search']['modes'].items()])

        if self._facets_for_mode:
            for facet_cfg in self._facets_for_mode:
                solr_facet_def: dict
                facet_alias = facet_cfg["alias"]

                if facet_cfg['type'] == "range":
                    solr_facet_def = _create_range_facet(facet_cfg)
                elif facet_cfg['type'] == "toggle":
                    solr_facet_def = _create_toggle_facet(facet_cfg)
                elif facet_cfg['type'] == "selector":
                    solr_facet_def = _create_selector_facet(facet_cfg)
                elif facet_cfg["type"] == "filter":
                    solr_facet_def = _create_filter_facet(facet_cfg)
                else:
                    continue

                json_facets[facet_alias] = solr_facet_def

        # Add a facet for the 'mode' block. This is special since we always want to return the counts for the query
        # regardless of the current filter selected. So if the user selects the 'person' mode, we still want to
        # show the count for the number of sources. This also allows us to omit a mode if there are zero results.
        json_facets["mode"] = {
            "type": "terms",
            "field": "type",
            "domain": {
                "excludeTags": MODE_FILTER_TAG,
                "filter": all_modes
            }
        }

        return json_facets

    def _compile_sorts(self) -> str:
        return ",".join(self.sorts)

    def compile(self) -> Dict:
        """
        Assembles the incoming data into a form that is appropriate for
        Solr.
        :return: A dictionary containing keys and values that is suitable for
            use as a Solr query.
        """
        mode_filter: str = self._modes_to_filter()
        # The tag allows us to reference this in the facets so that we can return all the types of results.
        # See https://solr.apache.org/guide/8_8/faceting.html#tagging-and-excluding-filters
        self.filters.append(f"{{!tag={MODE_FILTER_TAG}}}{mode_filter}")

        requested_filters: List = self._compile_filters()
        self.filters += requested_filters

        # These have already been checked in the validation, so they shouldn't raise an exception here.
        page_num: int = parse_page_number(self._page)
        return_rows: int = parse_row_number(self._req, self._return_rows)
        # Results are 0-indexed, so a request for 'start 0 + 20 rows' will return the first through the 20th result.
        # Then we simply take the page number and multiple it by the rows:
        #  start: page:1 = start:0
        #  start: page:2 = ((2 - 1) * 20) = start:20
        #  start: page:3 = ((3 - 1) * 20) = start:40
        start_row: int = 0 if page_num == 1 else ((page_num - 1) * return_rows)

        return {
            "query": self._requested_query,
            "filter": self.filters,
            "offset": start_row,
            "limit": return_rows,
            "sort": self._compile_sorts(),
            "facet": self._get_facets()
        }


def _create_range_facet(facet_cfg: Dict) -> Dict:
    """
    Creates a JSON facet API configuration that will return the min
    and max values of a scalar field (e.g., integers, dates, etc.)

    This range facet will EXCLUDE any filters tagged with the {!tag=RANGE_FILT}.
    This makes it possible to do a query with a bunch of other facets and filters,
    but to continue showing the maximum range possible for the specific field. This
    allows users to continue to move the "start" and "end" slider through the whole
    range of values, instead of being constrained by the max and min of the currently
    applied filters.

    This is configured as a 'query' facet because Solr is a bit dumb and won't otherwise
    let you create dedicated stats blocks. See:

    https://stackoverflow.com/questions/46450477/in-addition-to-the-query-retrieve-min-and-max-of-a-field-with-local-paramete

    :param facet_cfg: A facet configuration block from the config file.
    :return: A JSON Facet API configuration block.
    """
    field_name: str = facet_cfg["field"]

    cfg: Dict = {
        "type": "query",
        "q": "*:*",
        "facet": {
            "min": f"min({field_name})",
            "max": f"max({field_name})"
        },
        "domain": {
            "excludeTags": [RANGE_FILTER_TAG]
        }
    }
    return cfg


def _create_toggle_facet(facet_cfg: Dict) -> Dict:
    field_name: str = facet_cfg["field"]

    cfg: Dict = {
        "type": "terms",
        "field": f"{field_name}",
        "limit": 2
    }

    return cfg


def _create_selector_facet(facet_cfg: Dict) -> Dict:
    field_name: str = facet_cfg["field"]

    cfg: Dict = {
        "type": "terms",
        "field": f"{field_name}",
        "domain": {
            "excludeTags": [SELECTOR_FILTER_TAG]
        }
    }

    if sort := facet_cfg.get("sort"):
        cfg.update({"sort": sort})

    return cfg


def _create_filter_facet(facet_cfg: Dict) -> Dict:
    field_name: str = facet_cfg["field"]
    cfg: Dict = {
        "type": "terms",
        "field": f"{field_name}",
    }

    if sort := facet_cfg.get("sort"):
        cfg.update({"sort": sort})

    return cfg
