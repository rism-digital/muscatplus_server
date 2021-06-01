from typing import Dict, Optional, List

import serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import secondary_literature_json_value_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult

# 500, 505, 525, 691, 510, 596, 657, 651, 518, 856(?)
from search_server.resources.liturgical_festivals.liturgical_festival import LiturgicalFestival
from search_server.resources.shared.relationship import Relationship


class ReferencesNotesSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:ReferencesNotesSection"
    )
    notes = serpy.MethodField()
    performance_locations = serpy.MethodField(
        label="performanceLocations"
    )
    liturgical_festivals = serpy.MethodField(
        label="liturgicalFestivals"
    )

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.references_and_notes")

    def get_notes(self, obj: SolrResult) -> Optional[Dict]:
        # 500, 505, 518, 525
        req = self.context.get("request")
        transl = req.app.ctx.translations

        field_config: LabelConfig = {
            "source_general_notes_smni": ("records.general_note", None),
            "contents_notes_sm": ("records.contents_note", None),
            "performance_notes_sm": ("records.note_on_performance", None),
            "supplementary_material_sm": ("records.supplementary_material", None),
            "bibliographic_references_json": ("records.bibliographic_reference", secondary_literature_json_value_translator)
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_performance_locations(self, obj: SolrResult) -> Optional[Dict]:
        # 651
        if 'location_of_performance_json' not in obj:
            return None

        return PerformanceLocationsSection(obj,
                                           context={"request": self.context.get('request')}).data

    def get_liturgical_festivals(self, obj: SolrResult) -> Optional[Dict]:
        # 657
        if 'liturgical_festivals_json' not in obj:
            return None

        return LiturgicalFestivalsSection(obj,
                                          context={"request": self.context.get("request")}).data


class PerformanceLocationsSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:PerformanceLocationsSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.location_performance")

    def get_items(self, obj: Dict) -> List[Dict]:
        performance_locations = obj.get("location_of_performance_json", [])

        return Relationship(performance_locations,
                            many=True,
                            context={"request": self.context.get("request")}).data


class LiturgicalFestivalsSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:LiturgicalFestivalsSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.location_performance")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        liturgical_festivals = obj.get("liturgical_festivals_json", [])

        return LiturgicalFestival(liturgical_festivals,
                                  many=True,
                                  context={"request": self.context.get("request")}).data
