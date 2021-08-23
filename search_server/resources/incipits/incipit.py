import logging
import re
from typing import Dict, Optional, List

import serpy
from small_asc.client import JsonAPIRequest, Results

from search_server.helpers.display_fields import (
    get_display_fields,
    LabelConfig
)
from search_server.helpers.display_translators import key_mode_value_translator, clef_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import (
    ID_SUB,
    get_identifier
)
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.helpers.vrv import render_pae, RenderedPAE

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


def handle_incipits_list_request(req, source_id: str) -> Optional[Dict]:
    pass


async def handle_incipit_request(req, source_id: str, work_num: str) -> Optional[Dict]:
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

    def get_incip_id(self, obj: Dict) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        work_num: str = f"{obj.get('work_num_s')}"

        return get_identifier(req, "sources.incipit", source_id=source_id, work_num=work_num)

    def get_label(self, obj: SolrResult) -> Optional[Dict]:
        work_num: str = obj['work_num_s']
        source_title: str = obj["source_title_s"]
        title: str = f" ({d})" if (d := obj.get("title_s")) else ""

        return {"none": [f"{source_title}: {work_num}{title}"]}

    def get_part_of(self, obj: SolrResult) -> Optional[Dict]:
        if not self.context.get("direct_request"):
            return None

        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return {
            "label": transl.get("records.item_part_of"),  # TODO: This should probably be changed to 'incipit part of'
            "type": "rism:PartOfSection",
            "source": {
                "id": get_identifier(req, "sources.source", source_id=source_id),
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "label": {"none": [f"{obj.get('source_title_s')}"]}
            }
        }

    def get_summary(self, obj: SolrResult) -> Optional[List[Dict]]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "title_s": ("records.title_movement_tempo", None),
            "creator_name_s": ("records.composer_author", None),
            "text_incipit_s": ("records.text_incipit", None),
            "key_mode_s": ("records.key_or_mode", key_mode_value_translator),
            "scoring_summary_sm": ("records.scoring_summary", None),
            "clef_s": ("records.clef", clef_translator),
            "key_s": ("records.key_signature", None),
            "work_num_s": ("records.work_number", None),
            "role_s": ("records.role", None),
            "scoring_sm": ("records.scoring_in_movement", None),
            "general_notes_sm": ("records.general_note_incipits", None)
        }

        return get_display_fields(obj, transl, field_config)

    def get_rendered(self, obj: SolrResult) -> Optional[List]:
        # Use the pre-cached version.
        pae_code: Optional[str] = obj.get("original_pae_sni")
        if not pae_code:
            return None

        rendered_pae: Optional[RenderedPAE] = render_pae(pae_code)

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
