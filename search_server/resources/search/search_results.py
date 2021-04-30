import logging
import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.identifiers import (
    get_identifier,
    ID_SUB
)
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.search.base_search import BaseSearchResults


log = logging.getLogger(__name__)


class SearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    result_type = serpy.MethodField(
        label="type"
    )
    summary = serpy.MethodField()

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        kwargs: Dict = {}
        route: str = ""

        if obj["type"] == "source":
            kwargs = {"source_id": id_value}
            route = "sources.source"
        elif obj["type"] == "person":
            kwargs = {"person_id": id_value}
            route = "people.person"
        elif obj["type"] == "institution":
            kwargs = {"institution_id": id_value}
            route = "institutions.institution"
        elif obj["type"] == "place":
            kwargs = {"place_id": id_value}
            route = "places.place"
        elif obj["type"] == "liturgical_festival":
            kwargs = {"festival_id": id_value}
            route = "festivals.festival"
        elif obj["type"] == "incipit":
            # TODO: Process incipit for source id and incipit id
            kwargs = {"incipit_id": id_value}
            route = "incipits.incipit"

        return get_identifier(req, route, **kwargs)

    def get_label(self, obj: SolrResult) -> Dict:
        label: str

        if obj["type"] == "source":
            label = obj.get("main_title_s")
        elif obj["type"] == "institution":
            label = _format_institution_label(obj)
        elif obj["type"] in ("person", "institution", "liturgical_festival"):
            label = obj.get("name_s")
        else:
            label = "[ Test Title ]"

        return {"none": [label]}

    def get_result_type(self, obj: Dict) -> str:
        return f"rism:{obj.get('type').title()}"

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations
        label: Dict

        if obj["type"] == "source":
            label = transl.get("records.source")
        elif obj["type"] == "person":
            label = transl.get("records.person")
        elif obj["type"] == "institution":
            label = transl.get("records.institution")
        elif obj["type"] == "place":
            label = transl.get("records.place")
        elif obj["type"] == "incipit":
            label = transl.get("records.incipit")
        elif obj["type"] == "liturgical_festival":
            label = transl.get("records.liturgical_festival")
        else:
            label = {}
            log.debug(obj["type"])

        return label

    def get_summary(self, obj: Dict) -> List[Dict]:
        return [{
            "label": {"en": ["A label"]},
            "value": {"none": ["A value"]}
        }, {
            "label": {"de": ["A German label"]},
            "value": {"none": ["A German value"]}
        }]


class SearchResults(BaseSearchResults):
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return SearchResult(obj.docs, many=True, context={"request": self.context.get("request")}).data


def _format_institution_label(obj: SolrResult) -> str:
    city = siglum = ""

    if 'city_s' in obj:
        city = f", {obj['city_s']}"
    if 'siglum_s' in obj:
        siglum = f" ({obj['siglum_s']})"

    return f"{obj['name_s']}{city}{siglum}"
