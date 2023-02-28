import logging
import re
from typing import Optional

import serpy
from small_asc.client import Results, JsonAPIRequest

from search_server.resources.institutions.base_institution import BaseInstitution, SOLR_FIELDS_FOR_BASE_INSTITUTION
from search_server.resources.people.base_person import SOLR_FIELDS_FOR_BASE_PERSON
from search_server.resources.shared.relationship import Relationship
from search_server.resources.sources.base_source import BaseSource, SOLR_FIELDS_FOR_BASE_SOURCE
from shared_helpers.display_fields import LabelConfig, get_display_fields
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult, SolrConnection

log = logging.getLogger("mp_server")


async def handle_place_request(req, place_id: str) -> Optional[dict]:
    record: Optional[dict] = await SolrConnection.get(f"place_{place_id}")

    if not record:
        return None

    return await Place(record, context={"request": req,
                                        "direct_request": True}).data


class Place(serpy.AsyncDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    ptype = serpy.StaticField(
        label="type",
        value="rism:Place"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    label = serpy.MethodField()
    summary = serpy.MethodField()
    sources = serpy.MethodField()
    people = serpy.MethodField()
    institutions = serpy.MethodField()

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        place_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "places.place", place_id=place_id)

    def get_label(self, obj: SolrResult) -> dict:
        return {"none": [obj.get("name_s")]}

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations
        return transl.get("records.place")

    def get_summary(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "country_s": ("records.country", None),
            "district_s": ("records.place", None)  # TODO: Should be district
        }

        return get_display_fields(obj, transl, field_config)

    async def get_sources(self, obj: SolrResult) -> Optional[dict]:
        # if there are no sources attached to this place, return None
        source_count: int = obj.get("sources_count_i", 0)
        if source_count == 0:
            return None

        req = self.context.get("request")
        place_id: str = obj["id"]
        q: JsonAPIRequest = {
            "query": "*:*",
            "filter": ["type:source", f"location_of_performance_ids:{place_id}"],
            "fields": SOLR_FIELDS_FOR_BASE_SOURCE,
            "sort": "main_title_ans asc"
        }
        source_results: Results = await SolrConnection.search(q, cursor=True)

        source_list: list = await BaseSource(source_results,
                                             context={"request": req}, many=True).data

        return {
            "type": "rism:PlaceSourceList",
            "items": source_list
        }

    async def get_people(self, obj: SolrResult) -> Optional[dict]:
        people_count: int = obj.get("people_count_i", 0)
        if people_count == 0:
            return None

        req = self.context.get("request")
        place_id: str = obj["id"]
        q: JsonAPIRequest = {
            "query": "*:*",
            "filter": ["type:person", f"place_ids:{place_id}"],
            "fields": SOLR_FIELDS_FOR_BASE_PERSON,
            "sort": "name_ans desc"
        }
        person_results: Results = await SolrConnection.search(q, cursor=True)
        person_list: list = Relationship(person_results, context={"request": req}, many=True).data

        return {
            "type": "rism:PlacePersonList",
            "items": person_list
        }

    async def get_institutions(self, obj: SolrResult) -> Optional[dict]:
        institution_count: int = obj.get("institutions_count_i", 0)
        if institution_count == 0:
            return None

        req = self.context.get("request")
        place_id: str = obj["id"]
        q: JsonAPIRequest = {
            "query": "*:*",
            "filter": ["type:institution", f"place_ids:{place_id}"],
            "fields": SOLR_FIELDS_FOR_BASE_INSTITUTION,
            "sort": "name_ans asc"
        }
        institution_results: Results = await SolrConnection.search(q, cursor=True)
        institution_list: list = await BaseInstitution(institution_results,
                                                       context={"request": req},
                                                       many=True).data

        return {
            "type": "rism:PlaceInstitutionList",
            "items": institution_list
        }
