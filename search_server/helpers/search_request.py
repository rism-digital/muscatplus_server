import logging
import urllib.parse
from collections import defaultdict
from typing import Dict, Optional, List

from search_server.exceptions import InvalidQueryException, PaginationParseException
from search_server.helpers.vrv import get_pae_features
from search_server.resources.search.pagination import parse_page_number, parse_row_number

log = logging.getLogger(__name__)

DEFAULT_QUERY_STRING: str = "*:*"
TERM_FACET_LIMIT: int = 200   # The maximum number of results to return with a select facet ('term' facet in solr).

# Some of the facets and filters need to have a solr `{!tag}` prepended. We'll
# define them up-front.
class SolrQueryTags:
    RANGE_FILTER_TAG = "RANGE_FILTER"
    SELECT_FILTER_TAG = "SELECT_FILTER"
    MODE_FILTER_TAG = "MODE_FILTER"


class FacetModeValues:
    TEXT = "text"
    CHECK = "check"


class FacetBehaviourValues:
    INTERSECTION = "intersection"
    UNION = "union"


class FacetTypeValues:
    RANGE = "range"
    TOGGLE = "toggle"
    SELECT = "select"
    NOTATION = "notation"


class FacetSortValues:
    ALPHA = "alpha"
    COUNT = "count"


class IncipitModeValues:
    INTERVALS = "intervals"


def sorting_for_mode(cfg: dict, mode: str) -> list:
    return cfg["search"]["modes"][mode].get("sorting", [])


# Some helper functions to work with the field and filter configurations.
def filters_for_mode(cfg: Dict, mode: str) -> List:
    """
    Returns a set of facets to apply when a particular result mode is chosen.
    :param cfg: The application configuration
    :param mode: The selected mode
    :return: The list of filter fields from the configuration for a given mode, or an empty dictionary if no filters
        are configured.
    """
    return cfg["search"]["modes"][mode].get('filters', [])


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


def facet_modifier_map(requested_values: List) -> dict:
    """
    Used to combine other fields with facet modifiers. For example, a facet alias of 'source-type' might
    have a facet sort of 'fs=source-type:alpha' and a behaviour of 'fb=source-type:union'. This function is
    a generic one that creates a map of modifiers for specific parameters so that it can be looked up later.

    :param requested_values: A list of 'alias:modifier' values.
    :return: A dictionary mapping an alias to a modifier.
    """
    ret: dict = {}

    for value in requested_values:
        field_alias, modifier_value = value.split(":")
        ret[field_alias] = modifier_value

    return ret


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

    For the input API, the following query parameters are recognized:

     - `q`: The main query parameter. Required, Non-repeatable! "*:*" if not explicitly passed in.
     - `fq`: The main filter queries. Repeatable. Takes parameters like "name:Smith, John" and uses them as facet queries.
     - `fb`: The filter behaviours. Repeatable. Adjusts the named facet behaviour from 'intersection' and 'union'. For example,
             if we have `fq=name:Smith, John&fq=name:Smythe, Jane`, then we might also have `&fb=name:union` to adjust the
             behaviour of the facet. Acceptable values are `intersection` (default) and `union`.
     - `fs`: Similar in form to `fb`, but adjusts the sorting of the facet list
     - `mode`: Sets the mode of the search to return records of only that type.
     - `page`: Controls the return of the result page. Pages can be of multiple size, but this should always skip to the
               correct page.
     - `rows`: Number of results per page.
     - `sort`: Controls the sorting of returned results

    Some parameters are specific to only incipit searches
     - `im`: Incipit search mode. Controls the type of mode used for matching incipits. Currently only supports
             a value of 'intervals' (also the default)

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
        self.fields: list = ["*"]
        # Initialize a dictionary for caching the query PAE features so that we only have to do this once
        # Is null if this request is not for incipits, or if PAE features could not be extracted from an incipit.
        self.pae_features: Optional[dict] = None

        # If there is no q parameter it will return all results
        self._requested_query: str = req.args.get("q", DEFAULT_QUERY_STRING)
        self._requested_filters: list = req.args.getlist("fq", [])
        self._requested_facet_behaviours: list = req.args.getlist("fb", [])
        self._requested_facet_sorts: list = req.args.getlist("fs", [])
        self._requested_facet_mode: list = req.args.getlist("fm", [])
        self._requested_mode: str = req.args.get("mode", self._app_config["search"]["default_mode"])
        self._page: Optional[str] = req.args.get("page", None)
        self._return_rows: Optional[str] = req.args.get("rows", None)
        self._result_sorting: Optional[str] = req.args.get("sort", None)

        # parameters that are only valid with incipit searches, and are otherwise ignored.
        # It is always initialized with the default value.
        self._incipit_mode: str = req.args.get("im", IncipitModeValues.INTERVALS)

        # Configure the facets to show for the selected mode.
        self._facets_for_mode: list = filters_for_mode(self._app_config, self._requested_mode)
        self._alias_config_map: Dict = alias_config_map(self._facets_for_mode)
        self._behaviour_for_facet: dict = facet_modifier_map(self._requested_facet_behaviours)
        self._sort_for_facet: dict = facet_modifier_map(self._requested_facet_sorts)
        self._mode_for_facet: dict = facet_modifier_map(self._requested_facet_mode)

        # Configure the sorting for the different result modes (source, people, institutions, etc.)
        self._sorts_for_mode: list = sorting_for_mode(self._app_config, self._requested_mode)

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

        requested_sorts: List = self._req.args.getlist("sort", [])
        if len(requested_sorts) > 1:
            raise InvalidQueryException("Only one sort parameter can be supplied.")

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
        raw_statements: defaultdict = defaultdict(list)
        filter_statements: list = []

        # in a first pass, gather all the fields and values
        # into a dictionary {"fieldname":[value1, value2]}
        for filt in self._requested_filters:
            field, raw_value = filt.split(":")

            # If the field we're looking at is not one that we know about,
            # ignore it and go to the next one.
            if field not in self._alias_config_map:
                continue

            raw_statements[field].append(raw_value)

        for field, values in raw_statements.items():
            # if no behaviour is found, the default is 'intersection'
            behaviour: str = self._behaviour_for_facet.get(field, FacetBehaviourValues.INTERSECTION)
            # if no mode is found, the default is 'check'
            facetmode: str = self._mode_for_facet.get(field, FacetModeValues.CHECK)

            filter_config: dict = self._alias_config_map[field]
            filter_type: str = filter_config['type']
            solr_field_name: str = filter_config['field']
            solr_alt_field_name: Optional[str] = filter_config.get('alt_field', None)

            # do some processing and normalization on the value. First ensure we have a non-entity string.
            # This should convert the URL-encoded parameters back to 'normal' characters
            unencoded_values: list[str] = [urllib.parse.unquote_plus(s) for s in values]

            # Then remove any quotes (single or double) to ensure we control how the values actually get
            # to Solr.
            quoted_values: list[str] = [s.replace("\"", "").replace("'", "") for s in unencoded_values]

            # Some field types need to be tagged to help modify their behaviour and interactions with
            # facets for multi-select faceting. See:
            # https://solr.apache.org/guide/8_8/faceting.html#tagging-and-excluding-filters
            value: str
            tag: str

            field_has_values: bool = len(quoted_values) > 0

            if filter_type == FacetTypeValues.RANGE:
                value = quoted_values[0] if field_has_values else ""
                tag = f"{{!tag={SolrQueryTags.RANGE_FILTER_TAG}}}"
            elif filter_type == FacetTypeValues.TOGGLE:
                # We only accept 'true' as a value for toggles; anything else will
                # cause us to ignore this filter request. We do, however, try it against
                # all possible case variants.
                if not field_has_values:
                    continue

                raw_value: str = quoted_values[0]
                if raw_value.lower() != "true":
                    continue

                # uses the 'active value' to map a 'true' toggle to the actual field value
                # in solr. This means we can say 'foo=true' maps to 'foo_s:false'.
                value = filter_config['active_value']
                tag = ""
            else:
                join_op = " OR " if behaviour == FacetBehaviourValues.UNION else " AND "
                value = join_op.join([f"\"{val}\"" for val in quoted_values])
                tag = f"{{!tag={SolrQueryTags.SELECT_FILTER_TAG}}}" if behaviour == FacetBehaviourValues.UNION else ""

            query_string: str

            if facetmode == FacetModeValues.TEXT:
                query_string = f"{tag}{solr_alt_field_name}:({value})"
            else:
                query_string = f"{tag}{solr_field_name}:({value})"

            log.debug(query_string)

            filter_statements.append(query_string)

        return filter_statements

    def _compile_facets(self) -> dict:
        json_facets: dict = {}

        if self._facets_for_mode:
            for facet_cfg in self._facets_for_mode:
                solr_facet_def: dict
                facet_alias = facet_cfg["alias"]

                if facet_cfg['type'] == FacetTypeValues.RANGE:
                    solr_facet_def = _create_range_facet(facet_cfg)
                elif facet_cfg['type'] == FacetTypeValues.TOGGLE:
                    solr_facet_def = _create_toggle_facet(facet_cfg)
                elif facet_cfg['type'] == FacetTypeValues.SELECT:
                    behaviour: str = self._behaviour_for_facet.get(facet_alias, FacetBehaviourValues.INTERSECTION)

                    # Get the default sort from the config, and use that as the default sort value
                    # unless something different is specified.
                    default_sort: str = facet_cfg['default_sort']
                    sort: str = self._sort_for_facet.get(facet_alias, default_sort)
                    solr_facet_def = _create_select_facet(facet_cfg, behaviour, sort)
                else:
                    continue

                json_facets[facet_alias] = solr_facet_def

        # Add a facet for the 'mode' block. This is special since we always want to return the counts for the query
        # regardless of the current filter selected. So if the user selects the 'person' mode, we still want to
        # show the count for the number of sources. This also allows us to omit a mode if there are zero results.
        # a list of all possible modes configured.
        all_modes: str = " OR ".join([f"{v['record_type']}" for k, v in self._app_config['search']['modes'].items()])
        mode_query: str = f"type:({all_modes})"

        json_facets["mode"] = {
            "type": "terms",
            "field": "type",
            "domain": {
                "excludeTags": SolrQueryTags.MODE_FILTER_TAG,
                "filter": mode_query
            }
        }

        return json_facets

    def _compile_sorts(self) -> str:
        # if a sort parameter has been supplied, supply the solr sort parameters. Remember that this can be a list
        # of parameters; we iterate through all the possible sorts, and only select the one where the alias matches
        # the requested sort; then we construct a Solr sort statement from the list of statements for that block.
        # If no sort statement can be found, we return "score desc", which is the default for relevancy search.
        configuration_sorts: list = []

        if self._result_sorting:
            configuration_sorts = [", ".join(s['solr_sort']) for s in self._sorts_for_mode if s['alias'] == self._result_sorting]

        sort_parameters: list = self.sorts + configuration_sorts

        sort_statement: str = ", ".join(sort_parameters)

        return sort_statement if sort_statement else "score desc"

    def _compile_fields(self) -> str:
        return ",".join(self.fields)

    def compile(self) -> Dict:
        """
        Assembles the incoming data into a form that is appropriate for
        Solr.
        :return: A dictionary containing keys and values that is suitable for
            use as a Solr query.
        """
        # Check if a query has incoming note data; if so, and we are in incipit mode, we will perform an incipit search
        has_notedata: bool = self._req.args.get("n", None) is not None

        if self._requested_mode == "incipits" and has_notedata:
            # process intervals and modify the Solr search request accordingly.
            #
            # 1. Pass the incoming query to Verovio to render to PAE features
            # 2. Somehow check what sort of query requested (e.g., interval-only search) using the `im` param
            # 3. Adjust the query being passed to Solr to accommodate this query. This will probably encompass
            #   3a. Interpreting the incoming query parameters as one (or more) Solr "filter" parameters
            #   3b. Figuring out the statements to be used for the Solr 'sort' parameter
            #   3c. Doing all this while also supporting 'traditional' facet searches.

            # If we have an incipit mode, assume the incoming request is a PAE string.
            self.pae_features = get_pae_features(self._req)

            # If verovio returns empty features, then something went wrong. Assume the problem is with the input
            # query string, and flag an error to the user.
            if len(self.pae_features.get("intervals")) == 0:
                raise InvalidQueryException("The requested mode was 'incipits', but the query could not be interpreted as music notation.")

            intervals: Optional[list] = self.pae_features.get("intervals")
            pitches: Optional[list] = self.pae_features.get("pitches")

            # This will be refactored to take into account the other accepted values for the interval search modes,
            # once we know what they are.
            incipit_query: str = " ".join((str(s) for s in intervals))
            self.filters.insert(0, f'{{!min_hash field="intervals_mh" sim="0.9"}}:\"{incipit_query}\"')

            # Create the sort query
            first_half = []
            second_half = []
            for intn, intv in enumerate(intervals[:12], 1):
                first_half.append(f"interval{intn}_i")
                second_half.append(f"{intv}")

            first_half_q = ", ".join(first_half)
            second_half_q = ", ".join(second_half)
            score_stmt: str = f"sqedist({first_half_q}, {second_half_q})"
            # Ask Solr to do a squared euclidean distance on the intervals for the sort, to try and approximate
            # a relevancy calculation (that is, the distance between the intervals in the query to the distance of the
            # intervals in any given document.
            self.sorts.insert(0, f"{score_stmt} asc, id desc")
            self.fields.append(f"incipit_score:scale({score_stmt},0, 100)")

        mode_filter: str = self._modes_to_filter()
        # The tag allows us to reference this in the facets so that we can return all the types of results.
        # See https://solr.apache.org/guide/8_8/faceting.html#tagging-and-excluding-filters
        self.filters.append(f"{{!tag={SolrQueryTags.MODE_FILTER_TAG}}}{mode_filter}")

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

        solr_query = {
            "query": self._requested_query,
            "filter": self.filters,
            "offset": start_row,
            "limit": return_rows,
            "sort": self._compile_sorts(),
            "facet": self._compile_facets(),
            "fields": self._compile_fields()
        }

        return solr_query


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
            "excludeTags": [SolrQueryTags.RANGE_FILTER_TAG]
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


def _create_select_facet(facet_cfg: Dict, behaviour: str, sort: str) -> Dict:
    """
    Creates a Solr JSON Facet API definition for terms. This can be
    :param facet_cfg: The configuration block for Solr facets.
    :param behaviour:
    :param sort:
    :return:
    """
    field_name: str = facet_cfg["field"]

    cfg: Dict = {
        "type": "terms",
        "field": f"{field_name}",
        "limit": TERM_FACET_LIMIT
    }

    if behaviour == "union":
        cfg.update({
            "domain": {
                "excludeTags": [SolrQueryTags.SELECT_FILTER_TAG]
            }
        })

    # Unless 'alpha' is explicitly set, either as a requested sort or as a default in the configuration,
    # default to 'count'.
    if sort == FacetSortValues.ALPHA:
        cfg.update({"sort": {"index": "asc"}})
    else:
        cfg.update({"sort": {"count": "desc"}})

    return cfg

