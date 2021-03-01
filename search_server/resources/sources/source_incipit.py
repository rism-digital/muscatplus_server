import re
from typing import Dict, Optional, List
import logging
import pysolr
import serpy

import ujson
import verovio

from search_server.helpers.display_fields import get_display_fields, LabelConfig, key_mode_value_translator, \
    clef_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import (
    ID_SUB,
    get_identifier,
    get_jsonld_context,
    JSONLDContext
)
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult, SolrManager

log = logging.getLogger(__name__)

vrv_tk = verovio.toolkit()
vrv_tk.setInputFrom(verovio.PAE)
vrv_tk.setOptions(ujson.dumps({
    "footer": 'none',
    "header": 'none',
    "pageMarginTop": 10,
    "pageMarginBottom": 10,
    "pageMarginLeft": 10,
    "pageMarginRight": 10,
    "pageWidth": 1024 / 0.4,
    "spacingStaff": 1,
    "scale": 40,
    "adjustPageHeight": 1,
    "svgHtml5": "true",
    "svgFormatRaw": "true",
    "svgRemoveXlink": "true"
}))


def _incipit_to_pae(obj: SolrResult) -> str:
    """
    This function assumes that all the data is complete in the
    Solr result; any checks for whether the data needed to return
    the PAE code is present should be done before calling this function.
    :param obj: A Solr result object for an incipit.
    :return: A string formatted as Plaine and Easie code
    """
    clef = obj.get("clef_s")
    timesig = obj.get("timesig_s")
    key_or_mode = obj.get("key_mode_s")
    keysig = obj.get("key_s")
    incip = obj.get("music_incipit_s")

    pae_code: str = f"""
            @start:pae-file
            @clef:{clef}
            @keysig:{keysig}
            @key:{key_or_mode}
            @timesig:{timesig}
            @data:{incip}
            @end:pae-file
            """

    return pae_code


def _fetch_incipit(source_id: str, work_num: str) -> Optional[SolrResult]:
    fq: List = ["type:source_incipit",
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

    incipit = SourceIncipit(incipit_record, context={"request": req,
                                                     "direct_request": True})

    return incipit.data


class SourceIncipitList(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    lid = serpy.MethodField(
        label="id"
    )
    ltype = StaticField(
        label="type",
        value="rism:IncipitList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[JSONLDContext]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_lid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "incipits_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.incipits")

    def get_items(self, obj: SolrResult) -> Optional[List]:
        conn = SolrManager(SolrConnection)
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:source_incipit"]
        sort: str = "work_num_ans asc"

        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        return SourceIncipit(conn.results,
                             many=True,
                             context={"request": self.context.get("request")}).data


class SourceIncipit(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    incip_id = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    summary = serpy.MethodField()

    itype = StaticField(
        label="type",
        value="rism:Incipit"
    )
    title = serpy.StrField(
        attr="title_s",
        required=False
    )
    text_incipit = serpy.MethodField(
        label="textIncipit"
    )

    rendered = serpy.MethodField()

    def get_ctx(self, obj: Dict) -> Optional[Dict]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_incip_id(self, obj: Dict) -> str:
        req = self.context.get("request")

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        work_num: str = f"{obj.get('work_num_s')}"

        return get_identifier(req, "incipit", source_id=source_id, work_num=work_num)

    def get_label(self, obj: SolrResult) -> Optional[Dict]:
        title: Optional[str] = obj.get("title_s")
        t_incipit: Optional[str] = obj.get("text_incipit_s")

        if not title and not t_incipit:
            return {
                "none": ["[No title]"]
            }

        if title:
            label = title
        else:
            label = f"[{t_incipit}]"

        return {
            "none": [f"{label}"]
        }

    def get_summary(self, obj: SolrResult) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        field_config: LabelConfig = {
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

    def get_text_incipit(self, obj: SolrResult) -> Optional[Dict]:
        if not obj.get("text_incipit_s"):
            return None

        return {
            "none": [f"{obj.get('text_incipit_s')}"]
        }

    def get_rendered(self, obj: SolrResult) -> Optional[List]:
        if not obj.get("music_incipit_s"):
            return None

        pae_code: str = _incipit_to_pae(obj)

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
