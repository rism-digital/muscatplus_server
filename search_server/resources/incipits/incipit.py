import logging
import re
from typing import Optional

import serpy
from small_asc.client import JsonAPIRequest, Results

from search_server.helpers.display_fields import (
    get_display_fields,
    LabelConfig
)
from search_server.helpers.display_translators import key_mode_value_translator, clef_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.formatters import format_incipit_label
from search_server.helpers.identifiers import (
    ID_SUB,
    get_identifier
)
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.helpers.vrv import render_pae
from search_server.resources.sources.base_source import BaseSource

log = logging.getLogger(__name__)


def _fetch_incipit(source_id: str, work_num: str) -> Optional[SolrResult]:
    json_request: JsonAPIRequest = {
        "query": "*:*",
        "filter": ["type:incipit",
                   f"source_id:source_{source_id}",
                   f"work_num_s:{work_num}"],
        "sort": "work_num_ans asc",
        "limit": 1
    }
    record: Results = SolrConnection.search(json_request)

    if record.hits == 0:
        return None

    return record.docs[0]


async def handle_incipits_list_request(req, source_id: str) -> Optional[dict]:
    return {"incipits": "not implemented"}


async def handle_incipit_request(req, source_id: str, work_num: str) -> Optional[dict]:
    incipit_record: Optional[SolrResult] = _fetch_incipit(source_id, work_num)

    if not incipit_record:
        return None

    return Incipit(incipit_record, context={"request": req,
                                            "direct_request": True}).data


class Incipit(JSONLDContextDictSerializer):
    incip_id = serpy.MethodField(
        label="id"
    )
    itype = StaticField(
        label="type",
        value="rism:Incipit"
    )
    label = serpy.MethodField()
    part_of = serpy.MethodField(
        label="partOf"
    )
    summary = serpy.MethodField()
    rendered = serpy.MethodField()
    encodings = serpy.MethodField()

    def get_incip_id(self, obj: dict) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        work_num: str = f"{obj.get('work_num_s')}"

        return get_identifier(req, "sources.incipit", source_id=source_id, work_num=work_num)

    def get_label(self, obj: SolrResult) -> Optional[dict]:
        label: str = format_incipit_label(obj)

        return {"none": [label]}

    def get_part_of(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return {
            "label": transl.get("records.item_part_of"),  # TODO: This should probably be changed to 'incipit part of'
            "type": "rism:PartOfSection",
            "source": BaseSource(obj, context={"request": req}).data
        }

    def get_summary(self, obj: SolrResult) -> Optional[list[dict]]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "title_s": ("records.title_movement_tempo", None),
            "creator_name_s": ("records.composer_author", None),
            "text_incipit_s": ("records.text_incipit", None),
            "key_mode_s": ("records.key_or_mode", key_mode_value_translator),
            "scoring_summary_sm": ("records.scoring_summary", None),
            "work_num_s": ("records.work_number", None),
            "role_s": ("records.role", None),
            "scoring_sm": ("records.scoring_in_movement", None),
            "general_notes_sm": ("records.general_note_incipits", None)
        }

        if not obj.get("music_incipit_s"):
            field_config.update({
                "clef_s": ("records.clef", clef_translator),
                "key_s": ("records.key_signature", None)
            })

        return get_display_fields(obj, transl, field_config)

    def get_rendered(self, obj: SolrResult) -> Optional[list]:
        # Use the pre-cached version.
        pae_code: Optional[str] = obj.get("original_pae_sni")
        if not pae_code:
            return None
        is_mensural: bool = obj.get("is_mensural_b", False)

        # Set Verovio to render random IDs for this so that we don't have any ID collisions with
        # search result highlighting
        rendered_pae: Optional[tuple] = render_pae(pae_code, use_crc=False, is_mensural=is_mensural)

        if not rendered_pae:
            log.error("Could not load music incipit for %s", obj.get("id"))
            return None

        svg, b64midi = rendered_pae

        return [{
            "format": "image/svg+xml",
            "data": svg
        }, {
            "format": "audio/midi",
            "data": b64midi
        }]

    def get_encodings(self, obj: SolrResult) -> Optional[list]:
        if "music_incipit_s" not in obj:
            return None

        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        pae_encoding: dict = {}

        if c := obj.get("clef_s"):
            pae_encoding["clef"] = c
        if k := obj.get("key_s"):
            pae_encoding["keysig"] = k
        if t := obj.get("timesig_s"):
            pae_encoding["timesig"] = t
        if m := obj.get("key_mode_s"):
            pae_encoding["key"] = m
        if d := obj.get("music_incipit_s"):
            pae_encoding["data"] = d

        return [{
            "label": transl.get("records.plaine_and_easie"),
            "format": "application/json",
            "data": pae_encoding
        }]
