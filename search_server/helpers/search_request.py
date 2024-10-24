import functools
import logging
import urllib.parse
from collections import defaultdict
from typing import Optional

import small_asc.query
from small_asc.query import QueryParseError

from search_server.exceptions import InvalidQueryException, PaginationParseException
from search_server.helpers.vrv import get_pae_features
from search_server.resources.search.pagination import (
    parse_page_number,
    parse_row_number,
)
from shared_helpers.display_translators import SOURCE_SIGLA_COUNTRY_MAP

log = logging.getLogger("mp_server")

DEFAULT_QUERY_STRING: str = "*:*"
TERM_FACET_LIMIT: int = 200  # The maximum number of results to return with a select facet ('term' facet in solr).


# Some of the facets and filters need to have a solr `{!tag}` prepended. We'll
# define them up-front.
class SolrQueryTags:
    RANGE_FILTER_TAG = "RANGE_FILTER"
    SELECT_FILTER_TAG = "SELECT_FILTER"
    MODE_FILTER_TAG = "MODE_FILTER"
    QUERY_FILTER_TAG = "QUERY_FILTER"


class FacetBehaviourValues:
    INTERSECTION = "intersection"
    UNION = "union"


class FacetTypeValues:
    RANGE = "range"
    TOGGLE = "toggle"
    SELECT = "select"
    NOTATION = "notation"
    QUERY = "query"


class FacetSortValues:
    ALPHA = "alpha"
    COUNT = "count"


class IncipitModeValues:
    INTERVALS = "intervals"
    EXACT_PITCHES = "exact-pitches"
    CONTOUR = "contour"


def sorting_for_mode(cfg: dict, mode: str) -> list:
    return cfg["search"]["modes"][mode].get("sorting", [])


# Some helper functions to work with the field and filter configurations.
def filters_for_mode(cfg: dict, mode: str) -> list:
    """
    Returns a set of facets to apply when a particular result mode is chosen.
    :param cfg: The application configuration
    :param mode: The selected mode
    :return: The list of filter fields from the configuration for a given mode, or an empty dictionary if no filters
        are configured.
    """
    return cfg["search"]["modes"][mode].get("filters", [])


def filter_type_map(filters_config: list) -> dict:
    """
    A dictionary that maps the type of filter (toggle, selector, etc.) to the alias.
    :param filters_config:
    :return:
    """
    return {f"{cnf['alias']}": f"{cnf['type']}" for cnf in filters_config}


def types_alias_map(filters_config: list) -> dict:
    """
    Maps a given filter type to a list of aliases that use this type.
    Produces a dictionary of form {'select': ['aliasA', 'aliasB', ... ]}

    :param filters_config:
    :return:
    """
    filtmap = defaultdict(list)
    for f in filters_config:
        filtmap[f["type"]].append(f["alias"])

    return dict(filtmap)


def query_field_label_alias(cfg: dict, mode: str) -> list[dict]:
    qf: list = cfg["search"]["modes"][mode].get("q_fields", [])
    return []


def query_field_type_map(cfg: dict, mode: str) -> dict:
    qf: list = cfg["search"]["modes"][mode].get("q_fields", [])
    return {f"{q['alias']}": f"{q['field']}" for q in qf}


def filter_label_map(filters_config: list) -> dict:
    return {f"{cnf['alias']}": f"{cnf['label']}" for cnf in filters_config}


def alias_config_map(filters_config: list) -> dict:
    """
    A dictionary that maps the incoming API request 'alias' to the config block for that facet config.
    :param filters_config: A list of all the filters for the map

    :return:
    """
    return {f"{cnf['alias']}": cnf for cnf in filters_config}


def field_alias_map(filters_config: list) -> dict:
    """
    A dictionary mapping the configured alias to the Solr field. Used for referencing the solr field using the
    alias.
    :param filters_config: The application configuration
    :return: A dictionary of values mapping the alias to the solr field.
    """
    return {f"{cnf['alias']}": f"{cnf['field']}" for cnf in filters_config}


def facet_modifier_map(requested_values: list) -> dict:
    """
    Used to combine other fields with facet modifiers. For example, a facet alias of 'source-type' might
    have a facet behaviour of 'fb=source-type:union'. This function is
    a generic one that creates a map of modifiers for specific parameters so that it can be looked up later.

    :param requested_values: A list of 'alias:modifier' values.
    :return: A dictionary mapping an alias to a modifier.
    """
    ret: dict = {}

    for value in requested_values:
        field_alias, modifier_value = value.split(":")
        ret[field_alias] = modifier_value

    return ret


def suggest_fields_for_alias(facet_definitions: dict) -> dict:
    return {
        f"{cnf['alias']}": cnf["suggest_fields"]
        for _, cnf in facet_definitions.items()
        if cnf["type"] == "query"
    }


class SearchRequest:
    """
    Takes a number of parameters passed in from a RISM Online search request and compiles them to produce a set of
    parameters that can be sent to Solr. This is useful as a place to contain all the logic for how requests from the
    front-end get parsed and compiled to a valid Solr request, particularly around validating input and handling
    pagination.

    A bit of terminology to be aware of:
        - FILTERS are requests sent to Solr to filter queries
        - FACETS are responses from Solr giving us the values for specific facet fields

    In other words: Values from FACETS are sent to the client, which then uses this to compose requests for FILTERS
    back to the server.

    For the input API, the following query parameters are recognized:

     - `q`: The main query parameter. Required, Non-repeatable! "*:*" if not explicitly passed in.
     - `nc`: The requested national collection filter. This applies to anything that is limited nationally, such
             as sources and institutions. When a `nc` filter is applied, things *not* limited nationally, such as
             people or incipits, are omitted from the response.
     - `fq`: The main filter queries. Repeatable. Takes parameters like "name:Smith, John" and uses them as facet queries.
     - `fb`: The filter behaviours. Repeatable. Adjusts the named facet behaviour from 'intersection' and 'union'. For example,
             if we have `fq=name:Smith, John&fq=name:Smythe, Jane`, then we might also have `&fb=name:union` to adjust the
             behaviour of the facet. Acceptable values are `intersection` (default) and `union`.
     - `mode`: Sets the mode of the search to return records of only that type.
     - `page`: Controls the return of the result page. Pages can be of multiple size, but this should always skip to the
               correct page.
     - `rows`: Number of results per page.
     - `sort`: Controls the sorting of returned results

    Some parameters are specific to only incipit searches:
     - `n`: A Plaine and Easie string containing an encoded incipit search. Sent to Verovio to extract specific features
            which can then be sent to Solr as a query.
     - `im`: Incipit search mode. Controls the type of mode used for matching incipits. Supports a value of 'intervals'
            (also the default) and "exact-pitches". Controls which features we extract from Verovio to sent to Solr
            as a query.
     - `ic`: Controls the *rendering* of the incipit clef. Sent to Verovio only.
     - `it`: Controls the *rendering* of the incipit time signature. Sent to Verovio only.
     - `ik`: Controls the *rendering* of the incipit key signature. Sent to Verovio only, but the value of this will
            change the interval values of the resulting feature string returned from Verovio, which in turn will
            be sent to Solr.

    """

    default_sort = "id asc"

    def __init__(
        self,
        req,
        probe: bool = False,
        is_contents: bool = False,
    ):
        self._req = req
        self._app_config = req.app.ctx.config

        # Validate the incoming request to see if we can parse it.
        # This will raise an exception if there is anything wrong.
        self._validate_incoming_request()

        # Set up some public properties
        self.filters: list = []
        self.sorts: list = []
        self.fields: list = ["*"]
        self.query_report: Optional[dict] = None

        # A probe request will do all the reqular things EXCEPT it will hard-code the number of responses to 0
        # so that the actual results are not returned.
        self.probe: bool = probe

        # If the search request is a source contents search, then we need to adjust the
        # sorting parameters accordingly.
        self._is_contents: bool = is_contents

        # Initialize a dictionary for caching the query PAE features so that we only have to do this once
        # Is null if this request is not for incipits, or if PAE features could not be extracted from an incipit.
        self.pae_features: Optional[dict] = None

        self._requested_national_collection: list = req.args.getlist("nc", [])
        # Only one query parameter is allowed; however, to make it easier to add query
        # clauses, we use a list for the requested query parameters. These are
        # "AND"ed together later in the query process (See self._compile_query).
        self._requested_query: list = req.args.getlist("q", [])
        self._requested_filters: list = req.args.getlist("fq", [])
        self._requested_facet_behaviours: list = req.args.getlist("fb", [])
        self._requested_mode: str = req.args.get(
            "mode", self._app_config["search"]["default_mode"]
        )
        self._extra_params: dict = {"multiThreaded": True}
        self._page: Optional[str] = req.args.get("page", None)
        self._return_rows: Optional[str] = req.args.get("rows", None)
        self._result_sorting: Optional[str] = req.args.get("sort", None)

        # parameters that are only valid with incipit searches, and are otherwise ignored.
        # It is always initialized with the default value.
        self._incipit_mode: str = req.args.get("im", IncipitModeValues.INTERVALS)

        # Configure the facets to show for the selected mode.
        self._facets_for_mode: list = filters_for_mode(
            self._app_config, self._requested_mode
        )
        self._alias_config_map: dict = alias_config_map(self._facets_for_mode)

        self._query_fields_for_mode: dict = query_field_type_map(
            self._app_config, self._requested_mode
        )

        # Override the configured behaviour with the request behaviour. If a facet does not have a default_behaviour
        # defined, it will be 'intersection'.
        self._behaviour_from_config: dict = {
            k: v.get("default_behaviour", FacetBehaviourValues.INTERSECTION)
            for k, v in self._alias_config_map.items()
        }
        self._behaviour_from_request: dict = facet_modifier_map(
            self._requested_facet_behaviours
        )
        # Will merge both dictionaries, with the request behaviour overwriting any defaults in the config
        # behaviour.
        self._behaviour_for_facet: dict = {
            **self._behaviour_from_config,
            **self._behaviour_from_request,
        }

        # Configure the sorting for the different result modes (source, people, institutions, etc.)
        self._sorts_for_mode: list = sorting_for_mode(
            self._app_config, self._requested_mode
        )

    def _validate_incoming_request(self) -> None:
        """
        Raises an InvalidQueryException with specific responses for different error conditions.
        Doing this once means we can assume that if it passes, we don't have to raise this exception
        elsewhere in the class.

        :return: None
        """
        valid_q_param: list = self._req.args.getlist("q", [])
        if len(valid_q_param) > 1:
            raise InvalidQueryException("Only one query parameter can be supplied.")

        national_collection_param: list = self._req.args.getlist("nc", [])
        if len(national_collection_param) > 1:
            raise InvalidQueryException(
                "Only one national collection parameter can be supplied."
            )

        if len(national_collection_param) == 1:
            nc_valid_params = SOURCE_SIGLA_COUNTRY_MAP.keys()
            nc_incoming = set(national_collection_param)
            if nc_valid_params.isdisjoint(nc_incoming):
                raise InvalidQueryException(
                    "A valid country code must be used for the national collection parameter."
                )

        requested_modes: list = self._req.args.getlist("mode", [])
        if len(requested_modes) > 1:
            raise InvalidQueryException("Only one mode parameter can be supplied.")

        requested_sorts: list = self._req.args.getlist("sort", [])
        if len(requested_sorts) > 1:
            raise InvalidQueryException("Only one sort parameter can be supplied.")

        modes: dict = self._app_config["search"]["modes"]
        if len(requested_modes) == 1:
            requested_mode_config: Optional[dict] = modes.get(requested_modes[0])

            # if the requested mode does not match anything configured, raise an exception
            if not requested_mode_config:
                raise InvalidQueryException("Invalid value for the requested mode.")

        try:
            _ = parse_page_number(self._req.args.get("page", None))
        except PaginationParseException as e:
            raise InvalidQueryException(e) from e

        try:
            _ = parse_row_number(self._req, self._req.args.get("rows", None))
        except PaginationParseException as e:
            raise InvalidQueryException(e) from e

        for filt in self._req.args.getlist("fq", []):
            if ":" not in filt:
                raise InvalidQueryException(
                    f"Malformed filter query {filt}. A colon was not found to separate \
                    the field and value. The correct format is fq=field:value."
                )

    def _modes_to_filter(self) -> str:
        """
        Turns the incoming 'mode' request to a string suitable for use in a Solr `fq` query.

        :return: The alias mapping e.g., 'mode=people' to "type:person"
        """
        modes: dict = self._app_config["search"]["modes"]
        mode_cfg: dict = modes[self._requested_mode]
        record_type: str = mode_cfg["record_type"]

        return f"type:{record_type}"

    def _compile_filters(self) -> list:
        raw_statements: defaultdict = defaultdict(list)
        filter_statements: list = []

        # in a first pass, gather all the fields and values
        # into a dictionary {"fieldname":[value1, value2]}
        # Only split at the first occurrence since any other colons will be in the field value.
        for filt in self._requested_filters:
            field, raw_value = filt.split(":", 1)
            # If the field we're looking at is not one that we know about,
            # ignore it and go to the next one.
            if field not in self._alias_config_map:
                continue

            raw_statements[field].append(raw_value)

        for field, values in raw_statements.items():
            # if no behaviour is found, the default is 'intersection'
            behaviour: str = self._behaviour_for_facet.get(
                field, FacetBehaviourValues.INTERSECTION
            )

            filter_config: dict = self._alias_config_map[field]
            filter_type: str = filter_config["type"]
            solr_field_name: str

            if "function_query" in filter_config:
                solr_field_name = filter_config["function_query"]
            else:
                solr_field_name = filter_config["field"]

            # do some processing and normalization on the value. First ensure we have a non-entity string.
            # This should convert the URL-encoded parameters back to 'normal' characters
            unencoded_values: list[str] = [urllib.parse.unquote(s) for s in values]
            # Then remove any quotes (single or double) to ensure we control how the values actually get
            # to Solr.
            unquoted_values: list[str] = [s.replace('"', "") for s in unencoded_values]

            # If a value has a special character in it we need to requote it... If the value is not truthy, drop it.
            quoted_values: list[str] = []
            for v in unquoted_values:
                if v and (set(v) & {":", " ", "[", "]", "\\"}):
                    quoted_values.append(f'"{v}"')
                elif v:
                    quoted_values.append(f"{v}")
                else:
                    continue

            # Some field types need to be tagged to help modify their behaviour and interactions with
            # facets for multi-select faceting. See:
            # https://solr.apache.org/guide/8_8/faceting.html#tagging-and-excluding-filters
            value: str
            tag: str
            translation_table: dict
            join_op: str = (
                " OR " if behaviour == FacetBehaviourValues.UNION else " AND "
            )

            field_has_values: bool = len(quoted_values) > 0

            if filter_type == FacetTypeValues.RANGE:
                value = unquoted_values[0] if field_has_values else ""
                tag = f"{{!tag={SolrQueryTags.RANGE_FILTER_TAG}}}"
            elif filter_type == FacetTypeValues.TOGGLE:
                # We only accept 'true' as a value for toggles; anything else will
                # cause us to ignore this filter request. We do, however, try it against
                # all possible case variants.
                if not field_has_values:
                    continue

                quot_value: str = quoted_values[0]
                if quot_value.lower() != "true":
                    continue

                # uses the 'active value' to map a 'true' toggle to the actual field value
                # in solr. This means we can say 'foo=true' maps to 'foo_s:false'.
                value = filter_config.get("active_value", "")
                tag = ""
            elif filter_type == FacetTypeValues.QUERY:
                # The complexphrase query parser is also very sensitive to character escaping, so
                # we do some custom escaping here to make sure things are sent to Solr correctly. This means
                # double-escaping special characters which, when it's a backslash, also means triple-escaping it!
                translation_table = str.maketrans(
                    {
                        "/": "\\\\/",
                        "~": "\\\\~",
                        ":": "\\\\:",
                        "\\": "\\\\\\",
                        "[": "\\\\[",
                        "]": "\\\\]",
                    }
                )
                value = join_op.join(
                    [f"{val.translate(translation_table)}" for val in quoted_values]
                )
                tag = "{!complexphrase inOrder=true}"
            else:
                # Select values are not as problematic, so we only need to double-escape backslashes.
                translation_table = str.maketrans({"\\": "\\\\"})
                value = join_op.join(
                    [f"{val.translate(translation_table)}" for val in quoted_values]
                )
                tag = (
                    f"{{!tag={SolrQueryTags.SELECT_FILTER_TAG}}}"
                    if behaviour == FacetBehaviourValues.UNION
                    else ""
                )

            query_string: str
            # A function query can be used in the filter query, but
            # then it needs to take over the whole query string.
            if "function_query" in filter_config:
                query_string = filter_config["function_query"]
            else:
                query_string = f"{tag}{solr_field_name}:({value})"
            filter_statements.append(query_string)

        return filter_statements

    def _compile_facets(self) -> dict:
        json_facets: dict = {}

        if self._facets_for_mode:
            for facet_cfg in self._facets_for_mode:
                solr_facet_def: dict
                facet_alias = facet_cfg["alias"]

                if facet_cfg["type"] == FacetTypeValues.RANGE:
                    solr_facet_def = _create_range_facet(facet_cfg)
                elif facet_cfg["type"] == FacetTypeValues.TOGGLE:
                    solr_facet_def = _create_toggle_facet(facet_cfg)
                elif facet_cfg["type"] == FacetTypeValues.SELECT:
                    behaviour: str = self._behaviour_for_facet.get(
                        facet_alias, FacetBehaviourValues.INTERSECTION
                    )
                    solr_facet_def = _create_select_facet(facet_cfg, behaviour)
                else:
                    continue

                json_facets[facet_alias] = solr_facet_def

        # Add a facet for the 'mode' block. This is special since we always want to return the counts for the query
        # regardless of the current filter selected. So if the user selects the 'person' mode, we still want to
        # show the count for the number of sources. This also allows us to omit a mode if there are zero results.
        # a list of all possible modes configured.
        all_modes: str = " OR ".join(
            [
                f"{v['record_type']}"
                for k, v in self._app_config["search"]["modes"].items()
            ]
        )
        mode_query: str = f"type:({all_modes})"

        json_facets["mode"] = {
            "type": "terms",
            "field": "type",
            "domain": {
                "excludeTags": SolrQueryTags.MODE_FILTER_TAG,
                "filter": mode_query,
            },
        }

        return json_facets

    def _compile_sorts(self) -> str:
        # if a sort parameter has been supplied, supply the solr sort parameters. Remember that this can be a list
        # of parameters; we iterate through all the possible sorts, and only select the one where the alias matches
        # the requested sort; then we construct a Solr sort statement from the list of statements for that block.
        # If no sort statement can be found, we return "score desc", which is the default for relevancy search.
        configuration_sorts: list = []

        # If the sort parameter has been passed, look up the actual sort fields in the config for that
        # alias. If the sort parameter has *not* been passed, then use the sort configuration that is defined as
        # the default.
        if self._result_sorting:
            configuration_sorts = [
                ", ".join(s["solr_sort"])
                for s in self._sorts_for_mode
                if s["alias"] == self._result_sorting
            ]
        else:
            for s in self._sorts_for_mode:
                # Not interested in blocks that are not marked as a default search option.
                if "default" not in s:
                    continue

                # If this is a contents search, if the config is marked for only contents, and if it's marked as
                # default, then use this. Break afterwards, since we've found the default configuration for the
                # sorting.
                if (
                    self._is_contents
                    and s.get("only_contents", False) is True
                    and s.get("default", False) is True
                ) or (
                    not self._is_contents
                    and s.get("only_contents", False) is False
                    and s.get("default", False) is True
                ):
                    configuration_sorts = [", ".join(s["solr_sort"])]
                    break

        sort_parameters: list = self.sorts + configuration_sorts
        sort_statement: str = ", ".join(sort_parameters)

        return sort_statement

    def _compile_fields(self) -> str:
        return ",".join(self.fields)

    def _compile_query(self) -> str:
        if not self._requested_query:
            self.query_report = {"valid": True}
            return DEFAULT_QUERY_STRING

        query_string: str = " AND ".join(self._requested_query)

        try:
            parsed_query = small_asc.query.parse_with_field_replacements(
                query_string, self._query_fields_for_mode
            )
        except QueryParseError:
            self.query_report = {"valid": False}
            return query_string

        log.debug("Parsed query: %s", repr(parsed_query))
        self.query_report = {"valid": True}
        return parsed_query

    def compile(self) -> dict:
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
            self.pae_features: Optional[dict] = get_pae_features(self._req)
            if not self.pae_features:
                raise InvalidQueryException(
                    "The requested mode was 'incipits', but the PAE input was malformed."
                )

            # If verovio returns empty features, then something went wrong. Assume the problem is with the input
            # query string, and flag an error to the user.
            if self.pae_features.get("intervalsChromatic", []):
                raise InvalidQueryException(
                    "The requested mode was 'incipits', but the query could not be interpreted as music notation."
                )

            # This will be refactored to take into account the other accepted values for the interval search modes,
            # once we know what they are.
            incipit_query: str
            incipit_query_field: str = "intervals_bi"
            incipit_len_field: str = "intervals_len_i"
            query_len: int

            if self._incipit_mode == IncipitModeValues.EXACT_PITCHES:
                pitches: list = self.pae_features.get("pitchesChromatic", [])
                incipit_query = " ".join(pitches)
                incipit_query_field = "pitches_bi"
                incipit_len_field = "pitches_len_i"
                query_len = len(pitches)
            elif self._incipit_mode == IncipitModeValues.CONTOUR:
                contour: list = self.pae_features.get("intervalRefinedContour", [])
                incipit_query = " ".join(contour)
                incipit_query_field = "contour_refined_bi"
                query_len = len(contour)
            else:
                intervals: list = self.pae_features.get("intervalsChromatic", [])
                incipit_query = " ".join(str(s) for s in intervals)
                query_len = len(intervals)

            self._requested_query.insert(0, f'{incipit_query_field}:"{incipit_query}"')
            self._extra_params["qq"] = f'{incipit_query_field}:"{incipit_query}"'
            # query($qq) returns the score for the given subquery (qscore).
            # scoring function is (qscore / ((doc_len + query_len) - qscore))
            score_stmt: str = f"div(query($qq), sub(add({incipit_len_field}, {query_len}), query($qq)))"

            self.sorts.insert(0, f"{score_stmt} desc, id desc")
            self.fields.append(f"custom_score:scale({score_stmt},0,100)")

        mode_filter: str = self._modes_to_filter()
        requested_filters: list = self._compile_filters()
        self.filters += requested_filters

        # Check to see if we're setting the "type:" field manually in the incoming request. If we aren't, then append
        # the mode filter with the mode filter tag. Note that it also turns "off" the tagging of this field, so that
        # the numbers per type feature (where we can show the number of results if a different `type` was applied)
        # will effectively be disabled when manually setting the type.
        # NB: Most "type" fields in Solr are given as a dynamic field, e.g., "foo_type_id", so if we have that in
        # the query it will not falsely match since they do not end in "type:". BUT one should look here if, at
        # some point in the future, this changes and weird stuff happens with the search result types not working
        # correctly!
        manual_type: bool = any("type:" in f for f in self.filters)
        if not manual_type:
            # The tag allows us to reference this in the facets so that we can return all the types of results.
            # See https://solr.apache.org/guide/8_8/faceting.html#tagging-and-excluding-filters
            self.filters.append(
                f"{{!tag={SolrQueryTags.MODE_FILTER_TAG}}}{mode_filter}"
            )

        if self._requested_national_collection:
            nc_value: str = self._requested_national_collection[0]
            self.filters += [f'country_codes_sm:"{nc_value}"']

        # These have already been checked in the validation, so they shouldn't raise an exception here.
        page_num: int = parse_page_number(self._page)
        return_rows: int = parse_row_number(self._req, self._return_rows)
        # Results are 0-indexed, so a request for 'start 0 + 20 rows' will return the first through the 20th result.
        # Then we simply take the page number and multiply it by the rows:
        #  start: page:1 = start:0
        #  start: page:2 = ((2 - 1) * 20) = start:20
        #  start: page:3 = ((3 - 1) * 20) = start:40
        start_row: int = 0 if page_num == 1 else ((page_num - 1) * return_rows)

        solr_query = {
            "query": self._compile_query(),
            "filter": self.filters,
            "offset": start_row,
            "limit": return_rows if self.probe is False else 0,
            "sort": self._compile_sorts(),
            "facet": self._compile_facets(),
            "fields": self._compile_fields(),
            "params": self._extra_params,
        }

        return solr_query


def _create_range_facet(facet_cfg: dict) -> dict:
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

    cfg: dict = {
        "type": "query",
        "q": "*:*",
        "facet": {"min": f"min({field_name})", "max": f"max({field_name})"},
        "domain": {"excludeTags": [SolrQueryTags.RANGE_FILTER_TAG]},
    }
    return cfg


def _create_toggle_facet(facet_cfg: dict) -> dict:
    field_name: str
    cfg: dict = {"limit": 2}

    if "function_query" in facet_cfg:
        field_name = facet_cfg["function_query"]
        cfg["type"] = "query"
        cfg["q"] = field_name
    else:
        field_name = facet_cfg["field"]
        cfg["type"] = "terms"
        cfg["field"] = f"{field_name}"

    return cfg


def _create_select_facet(facet_cfg: dict, behaviour: str) -> dict:
    """
    Creates a Solr JSON Facet API definition for terms. This can be
    :param facet_cfg: The configuration block for Solr facets.
    :param behaviour:
    :return:
    """
    field_name: str = facet_cfg["field"]

    cfg: dict = {"type": "terms", "field": f"{field_name}", "limit": TERM_FACET_LIMIT}

    if behaviour == "union":
        cfg.update({"domain": {"excludeTags": [SolrQueryTags.SELECT_FILTER_TAG]}})

    return cfg


MATCH_CHARS = ['"', "'", "(", ")", "[", "]", "{", "}"]


@functools.lru_cache(maxsize=2048)
def _fix_string(instr: str) -> str:
    """A string checker that looks for balanced quotation marks
    and grouping indicators. It will continue to process the string recursively until all
    problems have been sorted out.

    NB: A note for future me: At some point someone is going to come
    along and ask why their carefully crafted query that looks for a string
    that is single-quoted doesn't work as they expect it to.

    So you may have to be a bit more clever about
    """

    # If the in string doesn't contain any of the characters,
    # then we don't need to do any processing.
    has_matches: bool = any(c in instr for c in MATCH_CHARS)
    if not has_matches:
        return instr

    # Solr doesn't like single quotes, but we can silently replace
    # them for our users when shipping off the query.
    if "'" in instr:
        fixed = instr.replace("'", '"')
        return _fix_string(fixed)

    if instr.count('"') % 2 != 0:
        # try fixing the string by adding the missing
        # quotation mark.
        fixed = instr[:-1] if instr.endswith('"') and len(instr) > 1 else f'{instr}"'
        return _fix_string(fixed)
    elif instr.endswith('""'):
        fixed = instr[:-2] if len(instr) > 2 else ""
        return _fix_string(fixed)

    for pair in [("(", ")"), ("[", "]"), ("{", "}")]:
        open, close = pair
        if instr.count(open) != instr.count(close):
            # Since we can't know how to balance the string,
            # just strip it of all the parentheses and then
            # try again.
            fixed = instr.replace(f"{open}", "").replace(f"{close}", "")
            return _fix_string(fixed)

    # This should represent a string that is OK!
    return instr
