import logging
import re
from typing import Dict, List, Optional

import serpy

from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import (
    ID_SUB,
    get_identifier,
    RELATIONSHIP_LABELS,
    QUALIFIER_LABELS
)
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult

log = logging.getLogger(__name__)


def handle_materialgroups_list_request(req, source_id: str) -> Optional[Dict]:
    pass


def handle_materialgroups_request(req, source_id: str, materialgroup_id: str) -> Optional[Dict]:
    pass


class SourceMaterialGroupList(ContextDictSerializer):
    mid = serpy.MethodField(
        label="id"
    )
    mtype = StaticField(
        label="type",
        value="rism:MaterialGroupList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_mid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "sources.materialgroups_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.material_description")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        material_groups: List[Dict] = obj.get("material_groups_json")
        items = SourceMaterialGroup(material_groups, many=True,
                                    context={"request": self.context.get('request')})

        return items.data


class SourceMaterialGroup(ContextDictSerializer):
    mid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    summary = serpy.MethodField()
    related = serpy.MethodField()

    def get_mid(self, obj: Dict) -> str:
        req = self.context.get("request")

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        materialgroup_id: str = f"{obj.get('group_num')}"

        return get_identifier(req, "sources.materialgroup", source_id=source_id, materialgroup_id=materialgroup_id)

    def get_label(self, obj: Dict) -> Optional[Dict]:
        group_num: Optional[str] = obj.get("group_num")
        if not group_num:
            return None

        return {"none": [f"Group {group_num}"]}

    def get_related(self, obj: Dict) -> Optional[Dict]:
        people_json = obj.get("people")
        institutions_json = obj.get("institutions")
        req = self.context.get("request")

        # These will always return a list, even if the data passed in is empty.
        people_items: List = _relationshiplist_from_json(people_json, "person", req)
        institution_items: List = _relationshiplist_from_json(institutions_json, "institution", req)

        all_items = people_items + institution_items

        if not all_items:
            return None

        transl: Dict = req.app.translations

        return {
            "label": transl.get("records.people_institutions"),
            "type": "rism:RelationshipList",
            "items": all_items
        }

    def get_summary(self, obj: Dict) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        fields: LabelConfig = {
            "source_type": ("records.source_type", None),
            "physical_extent": ("records.extent", None),
            "parts_held": ("records.parts_held", None),
            "parts_extent": ("records.parts_held_extent", None),
            "plate_numbers": ("records.plate_number", None),
            "printing_techniques": ("records.printing_technique", None),
            "book_formats": ("records.book_format", None),
            "general_notes": ("records.general_note", None),
            "binding_notes": ("records.binding_note", None),
            "watermark_notes": ("records.watermark_description", None),
            "place_publication": ("records.place_publication", None),
            "name_publisher": ("records.publisher", None),
            "date_statements": ("records.date", None),
        }

        return get_display_fields(obj, transl, field_config=fields)


def _relationshiplist_from_json(fielddata: List, reltype: str, req) -> List:
    if not fielddata:
        return []

    transl: Dict = req.app.translations

    items: List = []
    for rel in fielddata:
        source_rel: Dict = {
            "type": "rism:SourceRelationship"
        }
        name: Optional[str] = rel.get("name")
        role: Optional[str] = rel.get("role")
        qualifier: Optional[str] = rel.get("qualifier")

        if role:
            r_translation_key: str = RELATIONSHIP_LABELS.get(role)
            source_rel.update({
                "role": {
                    "type": f"relators:{role}",
                    "label": transl.get(r_translation_key)
                }
            })

        if qualifier:
            q_translation_key: str = QUALIFIER_LABELS.get(qualifier)
            source_rel.update({
                "qualifier": {
                    "type": f"rismdata:{qualifier}",
                    "label": transl.get(q_translation_key)
                }
            })

        if name:
            rel_id = rel.get("id")
            rel_num: str = re.sub(ID_SUB, "", rel_id)

            if reltype == "person":
                identifier = get_identifier(req, "people.person", person_id=rel_num)
                objtype = "rism:Person"
            else:
                identifier = get_identifier(req, "institutions.institution", institution_id=rel_num)
                objtype = "rism:Institution"

            source_rel.update({
                "relatedTo": {
                    "id": identifier,
                    "type": objtype,
                    "label": {"none": [name]}
                }
            })
        items.append(source_rel)

    return items
