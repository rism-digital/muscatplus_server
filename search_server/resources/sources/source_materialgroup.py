import re
from typing import Dict, List, Optional

import pysolr
import serpy

from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import (
    ID_SUB,
    get_identifier,
    JSONLDContext,
    get_jsonld_context,
    RELATIONSHIP_LABELS,
    QUALIFIER_LABELS
)

from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrManager, SolrResult

import logging
log = logging.getLogger(__name__)


def handle_materialgroups_list_request(req, source_id: str) -> Optional[Dict]:
    fq: List = ["type:source_materialgroup",
                f"source_id:source_{source_id}"]

    records: pysolr.Results = SolrConnection.search("*:*", fq=fq)

    if records.hits == 0:
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
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "materialgroups_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.material_description")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        conn = SolrManager(SolrConnection)
        fq: List = ["type:source_materialgroup",
                    f"source_id:{obj.get('source_id')}"]
        fl: str = "*,people_json:[json],institutions_json:[json],external_links_json:[json]"
        sort: str = "group_num_s asc"

        conn.search("*:*", fq=fq, fl=fl, sort=sort)

        if conn.hits == 0:
            return None

        items = SourceMaterialGroup(conn.results, many=True,
                                    context={"request": self.context.get('request')})

        return items.data


class SourceMaterialGroup(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    mid = serpy.MethodField(
        label="id"
    )
    mtype = StaticField(
        label="type",
        value="rism:MaterialGroup"
    )
    label = serpy.MethodField()
    summary = serpy.MethodField()
    related = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[JSONLDContext]:
        direct_request: Optional[bool] = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_mid(self, obj: SolrResult) -> str:
        req = self.context.get("request")

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        materialgroup_id: str = f"{obj.get('group_num_s')}"

        return get_identifier(req, "materialgroup", source_id=source_id, materialgroup_id=materialgroup_id)

    def get_label(self, obj: SolrResult) -> Optional[Dict]:
        group_num: Optional[str] = obj.get("group_num_s")
        if not group_num:
            return None

        return {"none": [f"Group {group_num}"]}

    def get_related(self, obj: SolrResult) -> Optional[Dict]:
        people_json = obj.get("people_json")
        institutions_json = obj.get("institutions_json")
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

    def get_summary(self, obj: SolrResult) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        fields: LabelConfig = {
            "source_type_sm": ("records.source_type", None),
            "physical_extent_sm": ("records.extent", None),
            "parts_held_sm": ("records.parts_held", None),
            "parts_extent_sm": ("records.parts_held_extent", None),
            "plate_numbers_sm": ("records.plate_number", None),
            "printing_techniques_sm": ("records.printing_technique", None),
            "book_formats_sm": ("records.book_format", None),
            "general_notes_sm": ("records.general_note", None),
            "binding_notes_sm": ("records.binding_note", None),
            "watermark_notes_sm": ("records.watermark_description", None),
            "place_publication_sm": ("records.place_publication", None),
            "name_publisher_sm": ("records.publisher", None),
            "date_statements_sm": ("records.date", None),
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
                identifier = get_identifier(req, "person", person_id=rel_num)
                objtype = "rism:Person"
            else:
                identifier = get_identifier(req, "institution", institution_id=rel_num)
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
