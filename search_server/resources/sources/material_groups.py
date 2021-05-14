import logging
from typing import Dict, List, Optional

import serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import printing_techniques_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.sources.relationships import RelationshipsSection

log = logging.getLogger("muscat_indexer")


class MaterialGroupsSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:MaterialGroupsSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult):
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.material_description")

    def get_items(self, obj: SolrResult) -> List[Dict]:
        mgdata: List = obj.get("material_groups_json")
        return MaterialGroup(mgdata,
                             many=True,
                             context={"request": self.context.get("request")}).data


class MaterialGroup(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    mtype = StaticField(
        label="type",
        value="rism:MaterialGroup"
    )
    summary = serpy.MethodField()
    relationships = serpy.MethodField()

    def get_label(self, obj: Dict) -> Dict:
        # TODO: Translate this header into the languages
        group_num: str = obj.get("group_num")
        return {"none": [f"Group {group_num}"]}

    def get_summary(self, obj: Dict) -> Optional[List]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "source_type": ("records.type", None),
            "publication_place": ("records.place_publication", None),
            "publisher_copyist": ("records.publisher_copyist", None),
            "date_statements": ("records.date", None),
            "printer_location": ("records.location_printer", None),
            "printer_name": ("records.name_printer", None),
            "physical_extent": ("records.format_extent", None),
            "physical_details": ("records.other_physical_details", None),
            "physical_dimensions": ("records.dimensions", None),
            "parts_held": ("records.parts_held", None),
            "printing_techniques": ("records.printing_technique", printing_techniques_translator),
            "book_formats": ("records.book_format", None),
            "plate_numbers": ("records.plate_number", None),
            "general_notes": ("records.general_note", None),
            "binding_notes": ("records.binding_note", None),
            "watermark_notes": ("records.watermark_description", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_relationships(self, obj: Dict) -> Optional[Dict]:
        # a set is disjoint if there are no keys in common.
        if {'related_people_json', 'related_institutions_json'}.isdisjoint(obj.keys()):
            return None
        return RelationshipsSection(obj, context={"request": self.context.get("request")}).data
