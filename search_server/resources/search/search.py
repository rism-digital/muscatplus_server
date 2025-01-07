import logging

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.resources.search.base_search import serialize_response
from search_server.resources.search.search_results import SearchResults

log = logging.getLogger("mp_server")


SEARCH_FIELDS = [
    "id",
    "type",
    "source_type_s",
    "content_types_sm",
    "record_type_s",
    "project_s",
    "project_type_s",
    "standard_titles_json",
    "source_member_composers_sm",
    "creator_name_s",
    "date_statements_sm",
    "num_source_members_i",
    "material_source_types_sm",
    "material_content_types_sm",
    "num_holdings_i",
    "is_contents_record_b",
    "source_membership_title_s",
    "source_membership_id",
    "source_membership_json",
    "has_digitization_b",
    "source_members_sm",
    "has_incipits_b",
    "has_iiif_manifest_b",
    "has_external_record_b",
    "profession_function_sm",
    "total_sources_i",
    "source_count_i",
    "gnd_country_codes_sm",
    "alternate_names_sm",
    "text_incipit_sm",
    "music_incipit_s",
    "voice_instrument_s",
    "main_title_s",
    "source_id",
    "original_pae_sni",
    "is_mensural_b",
    "intervals_im",
    "interval_ids_json",
    "pitches_sm",
    "pitches_ids_json",
    "contour_refined_sm",
]


async def handle_search_request(req) -> dict:
    try:
        request_compiler: SearchRequest = SearchRequest(req)
        request_compiler.fields = SEARCH_FIELDS
        solr_params: dict = request_compiler.compile()
    except InvalidQueryException:
        raise

    extra_context: dict = {
        "query_pae_features": request_compiler.pae_features,
        "direct_request": True,
    }

    return await serialize_response(req, solr_params, SearchResults, extra_context)
