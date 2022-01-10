import re
from typing import Optional
import logging

import serpy
from small_asc.client import Results

from search_server.resources.shared.relationship import Relationship
from search_server.resources.institutions.base_institution import BaseInstitution, SOLR_FIELDS_FOR_BASE_INSTITUTION
from search_server.resources.people.base_person import SOLR_FIELDS_FOR_BASE_PERSON, BasePerson
from search_server.resources.sources.base_source import BaseSource, SOLR_FIELDS_FOR_BASE_SOURCE
from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult, SolrConnection

log = logging.getLogger(__name__)


async def handle_place_request(req, place_id: str) -> Optional[dict]:
    record: Optional[dict] = SolrConnection.get(f"place_{place_id}")

    if not record:
        return None

    return Place(record, context={"request": req,
                                  "direct_request": True}).data


class Place(JSONLDContextDictSerializer):
    pid = serpy.MethodField(
        label="id"
    )
    ptype = StaticField(
        label="type",
        value="rism:Place"
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

    def get_summary(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "country_s": ("records.country", None),
            "district_s": ("records.place", None)  # TODO: Should be district
        }

        return get_display_fields(obj, transl, field_config)

    def get_sources(self, obj: SolrResult) -> Optional[dict]:
        # if there are no sources attached to this place, return None
        source_count: int = obj.get("sources_count_i", 0)
        if source_count == 0:
            return None

        req = self.context.get("request")
        place_id: str = obj["id"]
        q: dict = {
            "query": "*:*",
            "filter": ["type:source", f"location_of_performance_ids:{place_id}"],
            "params": {"fl": SOLR_FIELDS_FOR_BASE_SOURCE, "sort": "main_title_ans asc"},
            # "sort": "main_title_ans asc"
        }
        source_results: Results = SolrConnection.search(q, cursor=True)

        source_list: list = BaseSource(source_results, context={"request": req}, many=True).data

        return {
            "type": "rism:PlaceSourceList",
            "items": source_list
        }

    def get_people(self, obj: SolrResult) -> Optional[dict]:
        people_count: int = obj.get("people_count_i", 0)
        if people_count == 0:
            return None

        req = self.context.get("request")
        place_id: str = obj["id"]
        q: dict = {
            "query": "*:*",
            "filter": ["type:person", f"place_ids:{place_id}"],
            "params": {"fl": SOLR_FIELDS_FOR_BASE_PERSON},
            "sort": ["name_ans desc"]
        }
        person_results: Results = SolrConnection.search(q, cursor=True)
        person_list: list = Relationship(person_results, context={"request": req}, many=True).data

        return {
            "type": "rism:PlacePersonList",
            "items": person_list
        }

    def get_institutions(self, obj: SolrResult) -> Optional[dict]:
        institution_count: int = obj.get("institutions_count_i", 0)
        if institution_count == 0:
            return None

        req = self.context.get("request")
        place_id: str = obj["id"]
        q: dict = {
            "query": "*:*",
            "filter": ["type:institution", f"place_ids:{place_id}"],
            "params": {"fl": SOLR_FIELDS_FOR_BASE_INSTITUTION, "sort": "name_ans asc"},
        }
        institution_results: Results = SolrConnection.search(q, cursor=True)
        institution_list: list = BaseInstitution(institution_results,
                                                 context={"request": req},
                                                 many=True).data

        return {
            "type": "rism:PlaceInstitutionList",
            "items": institution_list
        }
