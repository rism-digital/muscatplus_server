import logging
import re

import ypres
from small_asc.client import JsonAPIRequest, Results

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.resources.institutions.base_institution import (
    BaseInstitution,
)
from search_server.resources.people.base_person import BasePerson
from search_server.resources.sources.base_source import (
    BaseSource,
)

log = logging.getLogger("mp_server")


async def handle_place_request(req, place_id: str) -> dict | None:
    record: dict | None = await SolrConnection.get(f"place_{place_id}")  # type: ignore

    if not record:
        return None

    return await Place(
        record, context={"request": req, "direct_request": True}
    ).serialized


class Place(ypres.AsyncDictSerializer):
    pid = ypres.MethodField(label="id")
    ptype = ypres.StaticField(label="type", value="rism:Place")
    type_label = ypres.MethodField(label="typeLabel")
    slabel = ypres.MethodField(label="label")
    summary = ypres.MethodField()
    sources = ypres.MethodField()
    people = ypres.MethodField()
    institutions = ypres.MethodField()

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        place_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(req, "places.place", place_id=place_id)

    def get_slabel(self, obj: SolrResult) -> dict:
        return {"none": [obj.get("name_s")]}

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        return transl["records.place"]

    def get_summary(self, obj: SolrResult) -> list | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "country_s": ("records.country", None),
            "district_s": ("records.place", None),  # TODO: Should be district
        }

        return get_display_fields(obj, transl, field_config)

    async def get_sources(self, obj: SolrResult) -> dict | None:
        # if there are no sources attached to this place, return None
        source_count: int = obj.get("sources_count_i", 0)
        if source_count == 0:
            return None

        req = self.context["request"]
        place_id: str = obj["id"]
        q: JsonAPIRequest = {
            "query": "*:*",
            "filter": ["type:source", f"location_of_performance_ids:{place_id}"],
            "sort": "main_title_ans asc",
        }
        source_results: Results = await SolrConnection.search(q, cursor=True)
        if source_results.hits == 0:
            return None

        source_list: list = await BaseSource(
            source_results.docs, context={"request": req}, many=True
        ).serialized_many

        return {"type": "rism:PlaceSourceList", "items": source_list}

    async def get_people(self, obj: SolrResult) -> dict | None:
        people_count: int = obj.get("people_count_i", 0)
        if people_count == 0:
            return None

        req = self.context["request"]
        place_id: str = obj["id"]
        q: JsonAPIRequest = {
            "query": "*:*",
            "filter": ["type:person", f"place_ids:{place_id}"],
            "sort": "name_ans desc",
        }
        person_results: Results = await SolrConnection.search(q, cursor=True)

        if person_results.hits == 0:
            return None

        person_list: list = await BasePerson(
            person_results.docs, context={"request": req}, many=True
        ).serialized_many

        return {"type": "rism:PlacePersonList", "items": person_list}

    async def get_institutions(self, obj: SolrResult) -> dict | None:
        institution_count: int = obj.get("institutions_count_i", 0)
        if institution_count == 0:
            return None

        req = self.context["request"]
        place_id: str = obj["id"]
        q: JsonAPIRequest = {
            "query": "*:*",
            "filter": ["type:institution", f"place_ids:{place_id}"],
            "sort": "name_ans asc",
        }
        institution_results: Results = await SolrConnection.search(q, cursor=True)
        if institution_results.hits == 0:
            return None

        institution_list: list = await BaseInstitution(
            institution_results.docs, context={"request": req}, many=True
        ).serialized_many

        return {"type": "rism:PlaceInstitutionList", "items": institution_list}
