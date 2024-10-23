import functools
import logging
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from luqum.exceptions import IllegalCharacterError, ParseSyntaxError
from luqum.parser import parser
from luqum.tree import AndOperation
from luqum.utils import UnknownOperationResolver

from search_server.exceptions import InvalidQueryException, PaginationParseException
from search_server.helpers.query import (
    AliasedSolrFieldTreeTransformer,
    UnknownFieldInQueryException,
)
from search_server.helpers.vrv import get_pae_features
from search_server.resources.search.pagination import (
    parse_page_number,
    parse_row_number,
)
from shared_helpers.display_translators import SOURCE_SIGLA_COUNTRY_MAP

log = logging.getLogger("mp_server")


DEFAULT_QUERY_STRING: str = "*:*"
TERM_FACET_LIMIT: int = 200  # The maximum number of results to return with a select facet ('term' facet in solr).


@dataclass
class SearchRequest:
    is_probe: bool
    is_contents: bool
    requested_national_collection: list[str]
    requested_query: list[str]
    requested_filters: list[str]
    requested_facet_behaviours: list[str]
    requested_mode: str
    requested_page: Optional[str]
    requested_rows: Optional[str]
    requested_sorting: Optional[str]
    requested_note_data: Optional[str]
    incipit_mode: str
    pae_features: Optional[dict]
    extra_fields: list[str]
    extra_params: dict
    extra_sorts: list[str]
    facets_for_mode: list
    alias_config_map: dict
    query_fields_for_mode: dict
    behaviour_from_config: dict
    behaviour_from_request: dict
    behaviour_for_facet: dict
    sorts_for_mode: list
    app_config: dict


def create_search_request(
    req, probe: bool = False, is_contents: bool = False
) -> SearchRequest:
    app_config = req.app.ctx.config
    national_collection: list = req.args.getlist("nc", [])
    incoming_query = req.args.getlist("q", [])
    incoming_filters = req.args.getlist("fq", [])
    incoming_facet_behaviours = req.args.getlist("fb", [])
    incoming_mode = req.args.get("mode", app_config["search"]["default_mode"])
    incoming_page = req.args.get("page", None)
    incoming_rows = req.args.get("rows", None)
    incoming_sorts = req.args.get("sort", None)
    incoming_note_data = req.args.get("n", None)
    incipit_mode = req.args.get("im", IncipitModeValues.INTERVALS)
    pae_features = get_pae_features(req) if incoming_note_data else None
    extra_params = {}
    facets_for_mode = filters_for_mode(app_config, incoming_mode)
    alias_map = alias_config_map(facets_for_mode)
    qf_for_mode = query_fields_for_mode(app_config, incoming_mode)
    config_behaviour = {
        k: v.get("default_behaviour", FacetBehaviourValues.INTERSECTION)
        for k, v in alias_map.items()
    }
    request_behaviour = facet_modifier_map(incoming_facet_behaviours)
    behaviour_for_facet: dict = {**config_behaviour, **request_behaviour}
    mode_sorts = sorting_for_mode(app_config, incoming_mode)
    fields = []
    sorts = []

    return SearchRequest(
        is_probe=probe,
        is_contents=is_contents,
        requested_national_collection=national_collection,
        requested_query=incoming_query,
        requested_filters=incoming_filters,
        requested_facet_behaviours=incoming_facet_behaviours,
        requested_mode=incoming_mode,
        requested_page=incoming_page,
        requested_rows=incoming_rows,
        requested_sorting=incoming_sorts,
        requested_note_data=incoming_note_data,
        incipit_mode=incipit_mode,
        pae_features=pae_features,
        extra_fields=fields,
        extra_sorts=sorts,
        extra_params=extra_params,
        facets_for_mode=facets_for_mode,
        alias_config_map=alias_map,
        query_fields_for_mode=qf_for_mode,
        behaviour_from_config=config_behaviour,
        behaviour_from_request=request_behaviour,
        behaviour_for_facet=behaviour_for_facet,
        sorts_for_mode=mode_sorts,
        app_config=app_config,
    )


@dataclass
class SolrRequest:
    query: str


@dataclass
class IncipitQuery:
    query: str
    sort: str
    field: str


# Some of the facets and filters need to have a solr `{!tag}` prepended. We'll
# define them up-front.
class SolrQueryTags(StrEnum):
    RANGE_FILTER_TAG = "RANGE_FILTER"
    SELECT_FILTER_TAG = "SELECT_FILTER"
    MODE_FILTER_TAG = "MODE_FILTER"
    QUERY_FILTER_TAG = "QUERY_FILTER"


class FacetBehaviourValues(StrEnum):
    INTERSECTION = "intersection"
    UNION = "union"


class FacetTypeValues(StrEnum):
    RANGE = "range"
    TOGGLE = "toggle"
    SELECT = "select"
    NOTATION = "notation"
    QUERY = "query"


class FacetSortValues(StrEnum):
    ALPHA = "alpha"
    COUNT = "count"


class IncipitModeValues(StrEnum):
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


def query_fields_for_mode(cfg: dict, mode: str) -> dict:
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


def validate_incoming_request(incoming: SearchRequest) -> (bool, Optional[str]):
    """
    Raises an InvalidQueryException with specific responses for different error conditions.
    Doing this once means we can assume that if it passes, we don't have to raise this exception
    elsewhere in the class.

    :return: Boolean Valid / Invalid; Optional Message.
    """
    if len(incoming.requested_query) > 1:
        return False, "Only one query parameter can be supplied."

    if len(incoming.requested_national_collection) > 1:
        return False, "Only one national collection parameter can be supplied."

    if len(incoming.requested_national_collection) == 1:
        nc_valid_params = SOURCE_SIGLA_COUNTRY_MAP.keys()
        nc_incoming = set(incoming.requested_national_collection)
        if nc_valid_params.isdisjoint(nc_incoming):
            return (
                False,
                "A valid country code must be used for the national collection parameter.",
            )

    if len(incoming.requested_mode) > 1:
        return False, "Only one mode parameter can be supplied."

    if incoming.requested_sorting and len(incoming.requested_sorting) > 1:
        return False, "Only one sort parameter can be supplied."

    modes: dict = incoming.app_config["search"]["modes"]
    if rm := incoming.requested_mode:
        requested_mode_config: Optional[dict] = modes.get(rm[0])

        # if the requested mode does not match anything configured, raise an exception
        if not requested_mode_config:
            return False, "Invalid value for the requested mode."

    try:
        _ = parse_page_number(incoming.requested_page)
    except PaginationParseException:
        return False, "Invalid page number."

    try:
        _ = parse_row_number(incoming.app_config["search"], incoming.requested_rows)
    except PaginationParseException:
        return False, "Invalid row number"

    for filt in incoming.requested_filters:
        if ":" not in filt:
            return (
                False,
                f"Malformed filter query {filt}. A colon was not found to separate the field and value. The correct format is fq=field:value.",
            )

    if (
        incoming.requested_mode == "incipits"
        and incoming.requested_note_data is not None
    ):
        if incoming.pae_features is None:
            return (
                False,
                "The requested mode was 'incipits', but the PAE input was malformed.",
            )

        if "intervalsChromatic" not in incoming.pae_features:
            return (
                False,
                "The requested mode was 'incipits', but the query could not be interpreted as music notation.",
            )

    return True, None


def modes_to_filter(incoming: SearchRequest) -> str:
    """
    Turns the incoming 'mode' request to a string suitable for use in a Solr `fq` query.

    :return: The alias mapping e.g., 'mode=people' to "type:person"
    """
    modes: dict = incoming.app_config["search"]["modes"]
    mode_cfg: dict = modes[incoming.requested_mode]
    record_type: str = mode_cfg["record_type"]

    return f"type:{record_type}"


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


def compile_incipits(incoming: SearchRequest) -> IncipitQuery:
    # process intervals and modify the Solr search request accordingly.
    #
    # 1. Pass the incoming query to Verovio to render to PAE features
    # 2. Somehow check what sort of query requested (e.g., interval-only search) using the `im` param
    # 3. Adjust the query being passed to Solr to accommodate this query. This will probably encompass
    #   3a. Interpreting the incoming query parameters as one (or more) Solr "filter" parameters
    #   3b. Figuring out the statements to be used for the Solr 'sort' parameter
    #   3c. Doing all this while also supporting 'traditional' facet searches.

    # This will be refactored to take into account the other accepted values for the interval search modes,
    # once we know what they are.
    incipit_query: str
    incipit_query_field: str = "intervals_bi"
    incipit_len_field: str = "intervals_len_i"
    query_len: int

    if incoming.incipit_mode == IncipitModeValues.EXACT_PITCHES:
        pitches: list = incoming.pae_features.get("pitchesChromatic", [])
        incipit_query = " ".join(pitches)
        incipit_query_field = "pitches_bi"
        incipit_len_field = "pitches_len_i"
        query_len = len(pitches)
    elif incoming.incipit_mode == IncipitModeValues.CONTOUR:
        contour: list = incoming.pae_features.get("intervalRefinedContour", [])
        incipit_query = " ".join(contour)
        incipit_query_field = "contour_refined_bi"
        query_len = len(contour)
    else:
        intervals: list = incoming.pae_features.get("intervalsChromatic", [])
        incipit_query = " ".join(str(s) for s in intervals)
        query_len = len(intervals)

    incoming.requested_query.insert(0, f'{incipit_query_field}:"{incipit_query}"')
    incoming.extra_params["qq"] = f'{incipit_query_field}:"{incipit_query}"'
    # query($qq) returns the score for the given subquery (qscore).
    # scoring function is (qscore / ((doc_len + query_len) - qscore))
    score_stmt: str = (
        f"div(query($qq), sub(add({incipit_len_field}, {query_len}), query($qq)))"
    )

    return IncipitQuery(
        sort=f"{score_stmt} desc",
        field=f"custom_score:scale({score_stmt},0,100)",
        query=f'{incipit_query_field}:"{incipit_query}"',
    )


def compile_sorts(incoming: SearchRequest) -> list:
    # if a sort parameter has been supplied, supply the solr sort parameters. Remember that this can be a list
    # of parameters; we iterate through all the possible sorts, and only select the one where the alias matches
    # the requested sort; then we construct a Solr sort statement from the list of statements for that block.
    # If no sort statement can be found, we return "score desc", which is the default for relevancy search.
    configuration_sorts: list = []

    # If the sort parameter has been passed, look up the actual sort fields in the config for that
    # alias. If the sort parameter has *not* been passed, then use the sort configuration that is defined as
    # the default.
    if incoming.requested_sorting:
        configuration_sorts = [
            ", ".join(s["solr_sort"])
            for s in incoming.sorts_for_mode
            if s["alias"] == incoming.requested_sorting
        ]
    else:
        for s in incoming.sorts_for_mode:
            # Not interested in blocks that are not marked as a default search option.
            if "default" not in s:
                continue

            # If this is a contents search, if the config is marked for only contents, and if it's marked as
            # default, then use this. Break afterwards, since we've found the default configuration for the
            # sorting.
            if (
                incoming.is_contents
                and s.get("only_contents", False) is True
                and s.get("default", False) is True
            ) or (
                not incoming.is_contents
                and s.get("only_contents", False) is False
                and s.get("default", False) is True
            ):
                configuration_sorts = [", ".join(s["solr_sort"])]
                break

    return incoming.extra_sorts + configuration_sorts


def compile_fields(incoming: SearchRequest) -> str:
    return ",".join(incoming.extra_fields) if incoming.extra_fields else ""


def compile(incoming: SearchRequest) -> dict:
    """
    Assembles the incoming data into a form that is appropriate for
    Solr.
    :return: A dictionary containing keys and values that is suitable for
        use as a Solr query.
    """
    if incoming.requested_mode == "incipits" and incoming.requested_note_data:
        incipit_query = compile_incipits(incoming)
        incoming.extra_sorts.append(incipit_query.sort)
        incoming.extra_fields.insert(0, incipit_query.field)

    mode_filter: str = modes_to_filter(incoming)
    filters: list = compile_filters(incoming)

    # Check to see if we're setting the "type:" field manually in the incoming request. If we aren't, then append
    # the mode filter with the mode filter tag. Note that it also turns "off" the tagging of this field, so that
    # the numbers per type feature (where we can show the number of results if a different `type` was applied)
    # will effectively be disabled when manually setting the type.
    # NB: Most "type" fields in Solr are given as a dynamic field, e.g., "foo_type_id", so if we have that in
    # the query it will not falsely match since they do not end in "type:". BUT one should look here if, at
    # some point in the future, this changes and weird stuff happens with the search result types not working
    # correctly!
    manual_type: bool = any("type:" in f for f in filters)
    if not manual_type:
        # The tag allows us to reference this in the facets so that we can return all the types of results.
        # See https://solr.apache.org/guide/8_8/faceting.html#tagging-and-excluding-filters
        filters.append(f"{{!tag={SolrQueryTags.MODE_FILTER_TAG}}}{mode_filter}")

    if incoming.requested_national_collection:
        nc_value: str = incoming.requested_national_collection[0]
        filters.append(f'country_codes_sm:"{nc_value}"')

    # These have already been checked in the validation, so they shouldn't raise an exception here.
    page_num: int = parse_page_number(incoming.requested_page)
    return_rows: int = parse_row_number(
        incoming.app_config["search"], incoming.requested_rows
    )
    # Results are 0-indexed, so a request for 'start 0 + 20 rows' will return the first through the 20th result.
    # Then we simply take the page number and multiply it by the rows:
    #  start: page:1 = start:0
    #  start: page:2 = ((2 - 1) * 20) = start:20
    #  start: page:3 = ((3 - 1) * 20) = start:40
    start_row: int = 0 if page_num == 1 else ((page_num - 1) * return_rows)

    solr_query = {
        "query": compile_query(incoming),
        "filter": filters,
        "offset": start_row,
        "limit": return_rows if incoming.is_probe is False else 0,
        "sort": compile_sorts(incoming),
        "facet": compile_facets(incoming),
        "fields": compile_fields(incoming),
        "params": incoming.extra_params,
    }

    return solr_query


def compile_query(incoming: SearchRequest) -> str:
    if not incoming.requested_query:
        return DEFAULT_QUERY_STRING

    query_string: str = " AND ".join(incoming.requested_query)

    fixed_query = _fix_string(query_string)
    valid_query: bool = True
    tree = None

    try:
        tree = parser.parse(fixed_query)
    except IllegalCharacterError:
        valid_query = False
    except ParseSyntaxError:
        valid_query = False

    if not valid_query:
        log.debug("Returning un-parsed query.")
        return fixed_query

    resolver = UnknownOperationResolver(resolve_to=AndOperation)
    query_transformer = AliasedSolrFieldTreeTransformer(incoming.query_fields_for_mode)

    try:
        new_tree = query_transformer.visit(tree)
    except UnknownFieldInQueryException as err:
        raise InvalidQueryException("Unknown search field.") from err

    parsed_query: str = str(resolver(new_tree))
    log.debug("Parsed query: %s", repr(parsed_query))

    return parsed_query


def compile_filters(incoming: SearchRequest) -> list:
    raw_statements: defaultdict = defaultdict(list)
    filter_statements: list = []

    # in a first pass, gather all the fields and values
    # into a dictionary {"fieldname":[value1, value2]}
    # Only split at the first occurrence since any other colons will be in the field value.
    for filt in incoming.requested_filters:
        field, raw_value = filt.split(":", 1)
        # If the field we're looking at is not one that we know about,
        # ignore it and go to the next one.
        if field not in incoming.alias_config_map:
            continue

        raw_statements[field].append(raw_value)

    for field, values in raw_statements.items():
        # if no behaviour is found, the default is 'intersection'
        behaviour: str = incoming.behaviour_for_facet.get(
            field, FacetBehaviourValues.INTERSECTION
        )

        filter_config: dict = incoming.alias_config_map[field]
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
        join_op: str = " OR " if behaviour == FacetBehaviourValues.UNION else " AND "

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


def compile_facets(incoming: SearchRequest) -> dict:
    json_facets: dict = {}

    if incoming.facets_for_mode:
        for facet_cfg in incoming.facets_for_mode:
            solr_facet_def: dict
            facet_alias = facet_cfg["alias"]

            if facet_cfg["type"] == FacetTypeValues.RANGE:
                solr_facet_def = _create_range_facet(facet_cfg)
            elif facet_cfg["type"] == FacetTypeValues.TOGGLE:
                solr_facet_def = _create_toggle_facet(facet_cfg)
            elif facet_cfg["type"] == FacetTypeValues.SELECT:
                behaviour: str = incoming.behaviour_for_facet.get(
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
            for k, v in incoming.app_config["search"]["modes"].items()
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
