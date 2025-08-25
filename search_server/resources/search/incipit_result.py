import logging

import ypres

from search_server.helpers.display_fields import get_search_result_summary
from search_server.helpers.display_translators import title_json_value_translator
from search_server.helpers.formatters import format_incipit_label
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.incipit_search_fields import IncipitModeValues
from search_server.helpers.record_types import create_source_types_block
from search_server.helpers.solr_connection import SolrResult
from search_server.helpers.vrv import render_incipit

log = logging.getLogger("mp_server")


class IncipitSearchResult(ypres.DictSerializer):
    srid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    result_type = ypres.StaticField(label="type", value="rism:Incipit")
    type_label = ypres.MethodField(label="typeLabel")
    part_of = ypres.MethodField(label="partOf")
    summary = ypres.MethodField()
    rendered = ypres.MethodField()
    score = ypres.MethodField()

    def get_srid(self, obj: dict) -> str:
        req = self.context["request"]
        work_num: str = strip_prefix(obj["work_num_s"])
        source_id: str = strip_prefix(obj["source_id"])

        return get_identifier(
            req, "sources.incipit", source_id=source_id, work_num=work_num
        )

    def get_slabel(self, obj: dict) -> dict:
        incipit_label: str = format_incipit_label(obj)
        return {"none": [incipit_label]}

    def get_type_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.incipit"]

    def get_summary(self, obj: dict) -> dict | None:
        field_config: dict = {
            "creator_name_s": ("incipitComposer", "records.composer_author", None),
            "standard_titles_json": (
                "sourceTitle",
                "records.source",
                title_json_value_translator,
            ),
            "text_incipit_sm": ("textIncipit", "records.text_incipit", None),
            "voice_instrument_s": ("voiceInstrument", "records.voice_instrument", None),
            "original_pae_sni": ("paeCode", "records.plaine_and_easie", None),
        }

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_search_result_summary(field_config, transl, obj)

    def get_part_of(self, obj: SolrResult) -> dict | None:
        """
        Provides a pointer back to the parent for this incipit
        """
        req = self.context["request"]
        parent_title: str = obj["main_title_s"]
        parent_source_id: str = strip_prefix(obj["source_id"])
        transl: dict = req.ctx.translations

        record_type: str = obj.get("record_type_s", "item")
        source_type: str = obj.get("source_type_s", "unspecified")
        content_types: list[str] = obj.get("content_types_sm", [])

        source_types_block: dict = create_source_types_block(
            record_type, source_type, content_types, transl
        )

        return {
            "sectionLabel": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": get_identifier(req, "sources.source", source_id=parent_source_id),
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "sourceTypes": source_types_block,
                "label": {"none": [parent_title]},
            },
        }

    def get_rendered(self, obj: SolrResult) -> list | None:
        if not obj.get("has_notation_b", False):
            log.debug("No music incipit")
            return None

        req = self.context["request"]

        # Grab the PAE features we computed from the incoming query request. These will
        # be used to perform the highlighting
        query_pae_features: dict | None = self.context.get("query_pae_features")

        # Find out what mode we're operating in to determine which fields we're using.
        search_mode: str = req.args.get("im", IncipitModeValues.INTERVALS)

        svg, midi = render_incipit(
            obj,
            query_pae_features,
            search_mode,
        )

        if not svg:
            return None

        return [
            {"format": "image/svg+xml", "data": svg},
            {"format": "audio/midi", "data": midi},
        ]

    def get_score(self, obj: SolrResult) -> float | None:
        return obj.get("custom_score")
