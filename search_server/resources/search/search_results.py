import logging
import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.identifiers import (
    get_identifier,
    ID_SUB
)
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.search.base_search import BaseSearchResults


log = logging.getLogger(__name__)


class SearchResults(BaseSearchResults):
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return SearchResult(obj.docs, many=True, context={"request": self.context.get("request")}).data


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
    part_of = serpy.MethodField(
        label="partOf"
    )

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

    def get_part_of(self, obj: SolrResult) -> Optional[Dict]:
        """
            Provides a pointer back to a parent. Used for Items in Sources and Incipits.
        """
        obj_type: str = obj["type"]

        if obj_type not in ("source", "incipit"):
            return None

        is_item: bool = obj.get('is_item_record_b', False)
        req = self.context.get("request")

        parent_title: str
        parent_source_id: str

        if obj_type == "source" and is_item:
            parent_title = obj.get("source_membership_title_s")
            parent_source_id = re.sub(ID_SUB, "", obj.get("source_membership_id"))
        elif obj_type == "incipit":
            parent_title = obj.get("source_title_s")
            parent_source_id = re.sub(ID_SUB, "", obj.get("source_id"))
        else:
            return None

        transl: Dict = req.app.ctx.translations

        return {
            "label": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": get_identifier(req, "sources.source", source_id=parent_source_id),
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "label": {"none": [parent_title]}
            }
        }

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

    def get_summary(self, obj: Dict) -> Optional[List[Dict]]:
        field_config: LabelConfig
        obj_type: str = obj['type']

        if obj_type == "source":
            field_config = {
                "creator_name_s": ("records.composer_author", None),
                "source_type_sm": ("records.source_type", None),  # TODO: The value of this field should be translatable
            }
        elif obj_type == "person":
            field_config = {
                "roles_sm": ("records.profession_or_function", None)
            }
        elif obj_type == "institution":
            field_config = {}
        elif obj_type == "place":
            field_config = {}
        else:
            return None

        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return get_display_fields(obj, transl, field_config=field_config)


def _format_institution_label(obj: SolrResult) -> str:
    city = siglum = ""

    if 'city_s' in obj:
        city = f", {obj['city_s']}"
    if 'siglum_s' in obj:
        siglum = f" ({obj['siglum_s']})"

    return f"{obj['name_s']}{city}{siglum}"
