from typing import Optional

import ypres

from search_server.resources.liturgical_festivals.liturgical_festival import (
    LiturgicalFestival,
)
from search_server.resources.shared.relationship import Relationship
from shared_helpers.display_fields import LabelConfig, get_display_fields
from shared_helpers.display_translators import (
    secondary_literature_json_value_translator,
    url_detecting_translator,
)
from shared_helpers.solr_connection import SolrResult
from shared_helpers.utilities import to_aiter


class ReferencesNotesSection(ypres.AsyncDictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:ReferencesNotesSection")
    notes = ypres.MethodField()
    performance_locations = ypres.MethodField(label="performanceLocations")
    liturgical_festivals = ypres.MethodField(label="liturgicalFestivals")

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.references_and_notes")

    def get_notes(self, obj: SolrResult) -> Optional[dict]:
        # 500, 505, 518, 525
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "source_general_notes_smni": (
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
        }

        return get_display_fields(obj, transl, field_config=field_config)

    async def get_performance_locations(self, obj: SolrResult) -> Optional[dict]:
        # 651
        if "location_of_performance_json" not in obj:
            return None

        return await PerformanceLocationsSection(
            obj, context={"request": self.context.get("request")}
        ).data

    def get_liturgical_festivals(self, obj: SolrResult) -> Optional[dict]:
        # 657
        if "liturgical_festivals_json" not in obj:
            return None

        return LiturgicalFestivalsSection(
            obj, context={"request": self.context.get("request")}
        ).data


class PerformanceLocationsSection(ypres.AsyncDictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:PerformanceLocationsSection")
    items = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.location_performance")

    async def get_items(self, obj: dict) -> list[dict]:
        performance_locations = obj.get("location_of_performance_json", [])

        return await Relationship(
            to_aiter(performance_locations),
            many=True,
            context={"request": self.context.get("request")},
        ).data


class LiturgicalFestivalsSection(ypres.DictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:LiturgicalFestivalsSection")
    items = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.liturgical_festivals")

    def get_items(self, obj: SolrResult) -> Optional[list]:
        liturgical_festivals = obj.get("liturgical_festivals_json", [])

        return LiturgicalFestival(
            liturgical_festivals,
            many=True,
            context={"request": self.context.get("request")},
        ).data
