from small_asc.client import JsonAPIRequest

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.resources.search.base_search import serialize_response
from search_server.resources.search.search_results import SearchResults


async def handle_search_request(req) -> dict:
    try:
        request_compiler: SearchRequest = SearchRequest(req)
        solr_params: JsonAPIRequest = request_compiler.compile()
    except InvalidQueryException:
        raise

    extra_context: dict = {
        "query_pae_features": request_compiler.pae_features,
        "direct_request": True,
        "search_request": True,
    }

    return await serialize_response(req, solr_params, SearchResults, extra_context)  # type: ignore


# This is the result of a failed experiment with requesting only certain
# fields in search results. It seemed to crash the searches since an exhaustive
# list was not provided.
# It is left here for posterity.
# FIELDS = [
#     "id",
#     "type",
#     "project_s",
#     "source_type_s",
#     "content_types_sm",
#     "record_type_s",
#     "main_title_s",
#     "source_member_composers_sm",
#     "source_membership_title_s",
#     "source_membership_id",
#     "source_members_sm",
#     "creator_name_s",
#     "date_statements_sm",
#     "num_source_members_i",
#     "material_source_types_sm",
#     "material_content_types_sm",
#     "num_holdings_i",
#     "is_contents_record_b",
#     "has_digitization_b",
#     "is_contents_record_b",
#     "has_incipits_b",
#     "has_iiif_manifest_b",
#     "has_external_record_b",
#     "num_holdings_i",
#     "record_uri_sni",
#     "name_s",
#     "gender_s",
#     "date_statement_s",
#     "profession_function_sm",
#     "total_sources_i",
#     "source_count_i",
#     "institution_name_s",
#     "department_s",
#     "city_s",
#     "siglum_s",
#     "gnd_country_codes_sm",
#     "alternate_names_sm",
#     "total_sources_i",
#     "work_num_s",
#     "source_id",
#     "titles_sm",
#     "creator_name_s",
#     "text_incipit_sm",
#     "voice_instrument_s",
#     "music_incipit_s",
#     "intervals_im",
#     "pitches_sm",
#     "contour_refined_sm",
#     "original_pae_sni",
#     "is_mensural_b",
#     "source_id",
#     "external_institution_id",
#     "intervals_bi",
#     "intervals_len_i",
#     "pitches_bi",
#     "pitches_len_i",
#     "contour_refined_bi",
#     "country_codes_sm",
# ]
