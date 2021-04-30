import logging
import re
from typing import Dict, Optional, List

import pysolr
import serpy
import ujson
import verovio

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
from search_server.helpers.solr_connection import SolrConnection, SolrResult, SolrManager

log = logging.getLogger(__name__)

# Disable chatty logging for Verovio.
verovio.enableLog(False)
vrv_tk = verovio.toolkit()
vrv_tk.setInputFrom(verovio.PAE)
vrv_tk.setOptions(ujson.dumps({
    "footer": 'none',
    "header": 'none',
    "breaks": 'none',
    "pageMarginTop": 0,
    "pageMarginBottom": 25,  # Artificially inflate the bottom margin until rism-digital/verovio#1960 is fixed.
    "pageMarginLeft": 0,
    "pageMarginRight": 0,
    "adjustPageWidth": "true",
    "spacingStaff": 1,
    "scale": 40,
    "adjustPageHeight": "true",
    "svgHtml5": "true",
    "svgFormatRaw": "true",
    "svgRemoveXlink": "true"
}))


def _fetch_incipit(source_id: str, work_num: str) -> Optional[SolrResult]:
    fq: List = ["type:incipit",
                f"source_id:source_{source_id}",
                f"work_num_s:{work_num}"]
    sort: str = "work_num_ans asc"

    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, sort=sort, rows=1)

    if record.hits == 0:
        return None

    return record.docs[0]


def handle_incipits_list_request(req, source_id: str) -> Optional[Dict]:
    pass


def handle_incipit_request(req, source_id: str, work_num: str) -> Optional[Dict]:
    incipit_record: Optional[SolrResult] = _fetch_incipit(source_id, work_num)

    if not incipit_record:
        return None

    return Incipit(incipit_record, context={"request": req,
                                            "direct_request": True}).data


class IncipitList(JSONLDContextDictSerializer):
    lid = serpy.MethodField(
        label="id"
    )
    ltype = StaticField(
        label="type",
        value="rism:IncipitList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_lid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "sources.incipits_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.incipits")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        conn = SolrManager(SolrConnection)
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:incipit"]
        sort: str = "work_num_ans asc"

        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        return Incipit(conn.results,
                       many=True,
                       context={"request": self.context.get("request")}).data


class Incipit(JSONLDContextDictSerializer):
    incip_id = serpy.MethodField(
        label="id"
    )
    itype = StaticField(
        label="type",
        value="rism:Incipit"
    )
    label = serpy.MethodField()
    within = serpy.MethodField()
    summary = serpy.MethodField()
    rendered = serpy.MethodField()

    def get_incip_id(self, obj: Dict) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        work_num: str = f"{obj.get('work_num_s')}"

        return get_identifier(req, "sources.incipit", source_id=source_id, work_num=work_num)

    def get_label(self, obj: SolrResult) -> Optional[Dict]:
        return {"none": [f"{obj.get('work_num_s')}"]}

    def get_within(self, obj: SolrResult) -> Optional[Dict]:
        if not self.context.get("direct_request"):
            return None

        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return {
            "id": get_identifier(req, "sources.source", source_id=source_id),
            "type": "rism:Source",
            "label": {"none": [f"{obj.get('source_title_s')}"]}
        }

    def get_summary(self, obj: SolrResult) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "title_s": ("records.title_movement_tempo", None),
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
        if not obj.get("music_incipit_s"):
            return None

        # Use the pre-cached version.
        pae_code: Optional[str] = obj.get("original_pae_sni")
        if not pae_code:
            return None

        load_status: bool = vrv_tk.loadData(pae_code)

        if not load_status:
            log.error("Could not load music incipit for %s", obj.get("id"))
            return None

        svg: str = vrv_tk.renderToSVG()
        mid: str = vrv_tk.renderToMIDI()
        b64midi = f"data:audio/midi;base64,{mid}"

        return [{
            "format": "image/svg+xml",
            "data": svg
        }, {
            "format": "audio/midi",
            "data": b64midi
        }]
