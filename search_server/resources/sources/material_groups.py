import logging
import re
from typing import Optional

import serpy

from shared_helpers.display_fields import LabelConfig, get_display_fields
from shared_helpers.display_translators import (
    printing_techniques_translator,
    material_source_types_translator,
    material_content_types_translator
)
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult
from search_server.resources.shared.external_link import ExternalResourcesSection
from search_server.resources.shared.relationship import RelationshipsSection

log = logging.getLogger("mp_server")


class MaterialGroupsSection(serpy.DictSerializer):
    # mgid = serpy.MethodField(
    #     label="id"
    # )
    label = serpy.MethodField()
    # stype = serpy.StaticField(
    #     label="type",
    #     value="rism:MaterialGroupsSection"
    # )
    items = serpy.MethodField()

    def get_mgid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(req, "sources.material_groups_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.material_description", {})

    def get_items(self, obj: SolrResult) -> list[dict]:
        mgdata: list = obj.get("material_groups_json", [])
        return MaterialGroup(mgdata,
                             many=True,
                             context={"request": self.context.get("request")}).data


class MaterialGroup(serpy.DictSerializer):
    # mgid = serpy.MethodField(
    #     label="id"
    # )
    label = serpy.MethodField()
    # mtype = serpy.StaticField(
    #     label="type",
    #     value="rism:MaterialGroup"
    # )
    summary = serpy.MethodField()
    notes = serpy.MethodField()
    relationships = serpy.MethodField()
    external_resources = serpy.MethodField(
        label="externalResources"
    )

    def get_mgid(self, obj: dict) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj["source_id"])
        mg_id: str = obj["group_num"]

        return get_identifier(req, "sources.material_group", source_id=source_id, mg_id=mg_id)

    def get_label(self, obj: dict) -> dict:
        # TODO: Translate this header into the languages
        group_num: str = obj.get("group_num")
        return {"none": [f"Group {group_num}"]}

    def get_summary(self, obj: dict) -> Optional[list]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "material_source_types": ("records.source_type", material_source_types_translator),
            "material_content_types": ("records.content_type", material_content_types_translator),
            "publication_place": ("records.place_publication", None),
            "publisher_copyist": ("records.publisher_copyist", None),
            "date_statements": ("records.date", None),
            "printer_location": ("records.location_printer", None),
            "printer_name": ("records.name_printer", None),
            "physical_extent": ("records.format_extent", None),
            "parts_held_extent": ("records.parts_held_extent", None),
            "physical_dimensions": ("records.dimensions", None),
            "physical_details": ("records.other_physical_details", None),
            # "parts_held": ("records.parts_held", None),
            # "parts_extent": ("records.extent_parts", None),,
            "printing_techniques": ("records.printing_technique", printing_techniques_translator),
            "book_formats": ("records.book_format", None),
            "plate_numbers": ("records.plate_number", None),
            "publisher_numbers": ("records.publisher_number", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_notes(self, obj: dict) -> Optional[list]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "general_notes": ("records.general_note", None),
            "binding_notes": ("records.binding_note", None),
            "watermark_notes": ("records.watermark_description", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_relationships(self, obj: dict) -> Optional[dict]:
        # a set is disjoint if there are no keys in common. Check if these keys exist in the
        # record; if they are disjoint, then we don't need to process them.
        if {'related_people_json', 'related_institutions_json'}.isdisjoint(obj.keys()):
            return None

        return RelationshipsSection(obj, context={"request": self.context.get("request")}).data

    def get_external_resources(self, obj: dict) -> Optional[dict]:
        if "external_resources" not in obj:
            return None

        return ExternalResourcesSection(obj, context={"request": self.context.get("request")}).data
