import ypres

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import (
    rism_series_translator,
    secondary_literature_json_value_translator,
    url_detecting_translator,
)
from search_server.helpers.identifiers import get_identifier
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.liturgical_festivals.liturgical_festival import (
    LiturgicalFestival,
)
from search_server.resources.shared.relationship import Relationship


class ReferencesNotesSection(ypres.DictSerializer):
    sid = ypres.MethodField(label="id")
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:ReferencesNotesSection")
    notes = ypres.MethodField()
    performance_locations = ypres.MethodField(label="performanceLocations")
    liturgical_festivals = ypres.MethodField(label="liturgicalFestivals")

    def get_sid(self, obj: SolrResult) -> str | None:
        req = self.context["request"]
        route_name = self.context["section_route"]
        route_params = self.context["route_params"]

        return get_identifier(req, route_name, **route_params)

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.references_and_notes"]

    def get_notes(self, obj: SolrResult) -> list | None:
        # 500, 505, 518, 525
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "source_general_notes_smni": (
                "records.general_note",
                url_detecting_translator,
            ),
            "work_general_notes_smni": (
                "records.general_note",
                url_detecting_translator,
            ),
            "publication_general_notes_smni": (
                "records.general_note",
                url_detecting_translator,
            ),
            "contents_notes_sm": ("records.contents_note", None),
            "source_of_description_notes_sm": ("records.copy_examined", None),
            "performance_notes_sm": ("records.note_on_performance", None),
            "supplementary_material_sm": ("records.supplementary_material", None),
            "works_catalogue_json": (
                "records.catalog_works",
                secondary_literature_json_value_translator,
            ),
            "bibliographic_references_json": (
                "records.bibliographic_reference",
                secondary_literature_json_value_translator,
            ),
            "rism_series_json": (
                "general.rism_series_a_b_references",
                rism_series_translator,
            ),
            "source_data_found_json": (
                "records.source_data_found",
                secondary_literature_json_value_translator,
            ),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_performance_locations(self, obj: SolrResult) -> dict | None:
        # 651
        if "location_of_performance_json" not in obj:
            return None

        return PerformanceLocationsSection(
            obj,
            context={
                "request": self.context["request"],
                "route_params": self.context.get("route_params", {}),
                "section_route": self.context.get("performance_locations_route"),
                "item_route": self.context.get("relationship_item_route"),
            },
        ).serialized

    def get_liturgical_festivals(self, obj: SolrResult) -> dict | None:
        # 657
        if "liturgical_festivals_json" not in obj:
            return None

        return LiturgicalFestivalsSection(
            obj,
            context={
                "request": self.context["request"],
                "route_params": self.context.get("route_params", {}),
                "section_route": self.context.get("liturgical_festivals_route"),
            },
        ).serialized


class PerformanceLocationsSection(ypres.DictSerializer):
    sid = ypres.MethodField(label="id")
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:PerformanceLocationsSection")
    items = ypres.MethodField()

    def get_sid(self, obj: dict) -> str | None:
        req = self.context["request"]
        route_name = self.context.get("section_route")
        route_params = self.context["route_params"]
        if not isinstance(route_name, str):
            return None
        return get_identifier(req, route_name, **route_params)

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.location_performance"]

    def get_items(self, obj: dict) -> list[dict]:
        performance_locations = obj.get("location_of_performance_json", [])

        return Relationship(
            performance_locations,
            many=True,
            context={"request": self.context["request"]},
        ).serialized_many


class LiturgicalFestivalsSection(ypres.DictSerializer):
    sid = ypres.MethodField(label="id")
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:LiturgicalFestivalsSection")
    items = ypres.MethodField()

    def get_sid(self, obj: SolrResult) -> str | None:
        req = self.context["request"]
        route_name = self.context.get("section_route")
        route_params = self.context["route_params"]
        if not isinstance(route_name, str):
            return None
        return get_identifier(req, route_name, **route_params)

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.liturgical_festivals"]

    def get_items(self, obj: SolrResult) -> list | None:
        liturgical_festivals = obj.get("liturgical_festivals_json", [])

        return LiturgicalFestival(
            liturgical_festivals,
            many=True,
            context={"request": self.context["request"]},
        ).serialized_many
