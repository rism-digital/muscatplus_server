import ypres

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import (
    material_content_types_translator,
    material_source_types_translator,
    printing_techniques_translator,
)
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.relationship import RelationshipsSection


class MaterialGroupsSection(ypres.DictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl.get("records.material_description", {})

    def get_items(self, obj: SolrResult) -> list[dict]:
        mgdata: list = obj.get("material_groups_json", [])
        # NB: The regular list needs to be converted to an async iterator
        return MaterialGroup(
            mgdata,
            many=True,
            context={"request": self.context["request"]},
        ).serialized_many


class MaterialGroup(ypres.DictSerializer):
    sid = ypres.MethodField(label="id")
    stype = ypres.StaticField(value="rism:MaterialGroup", label="type")
    slabel = ypres.MethodField(label="label")
    summary = ypres.MethodField()
    notes = ypres.MethodField()
    relationships = ypres.MethodField()
    external_resources = ypres.MethodField(label="externalResources")

    def get_sid(self, obj: dict) -> str:
        req = self.context["request"]
        group_num: str = obj["group_num"]
        source_id: str = strip_prefix(obj["source_id"])
        return get_identifier(
            req, "sources.material_group", source_id=source_id, mg_id=group_num
        )

    def get_slabel(self, obj: dict) -> dict:
        # TODO: Translate this header into the languages
        group_num: str = obj["group_num"]
        return {"none": [f"Group {group_num}"]}

    def get_summary(self, obj: dict) -> list | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "material_source_types": (
                "records.source_type",
                material_source_types_translator,
            ),
            "material_content_types": (
                "records.content_type",
                material_content_types_translator,
            ),
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
            "printing_techniques": (
                "records.printing_technique",
                printing_techniques_translator,
            ),
            "book_formats": ("records.book_format", None),
            "plate_numbers": ("records.plate_number", None),
            "publisher_numbers": ("records.publisher_number", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_notes(self, obj: dict) -> list | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "general_notes": ("records.general_note", None),
            "binding_notes": ("records.binding_note", None),
            "watermark_notes": ("records.watermark_description", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_relationships(self, obj: dict) -> dict | None:
        # a set is disjoint if there are no keys in common. Check if these keys exist in the
        # record; if they are disjoint, then we don't need to process them.
        if {"related_people_json", "related_institutions_json"}.isdisjoint(obj.keys()):
            return None

        return RelationshipsSection(
            obj,
            context={
                "request": self.context["request"],
                "route_params": {
                    "source_id": strip_prefix(obj["source_id"]),
                    "mg_id": obj["group_num"],
                },
                "section_route": "sources.material_group_relationships",
                "item_route": "sources.material_group_relationship",
            },
        ).serialized

    def get_external_resources(self, obj: dict) -> dict | None:
        if "external_resources" not in obj:
            return None

        return ExternalResourcesSection(
            obj, context={"request": self.context["request"]}
        ).serialized
