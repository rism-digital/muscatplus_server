import logging
import re
from typing import Optional

import ypres
from small_asc.client import JsonAPIRequest, Results

from search_server.helpers.record_types import create_source_types_block
from search_server.helpers.vrv import render_mei, render_pae, render_png
from search_server.resources.sources.base_source import BaseSource
from shared_helpers.display_fields import LabelConfig, get_display_fields
from shared_helpers.display_translators import (
    clef_translator,
    key_mode_value_translator,
)
from shared_helpers.formatters import format_incipit_label, format_source_label
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrConnection, SolrResult

log = logging.getLogger("mp_server")


async def _fetch_incipit(source_id: str, work_num: str) -> Optional[SolrResult]:
    json_request: JsonAPIRequest = {
        "query": "*:*",
        "filter": [
            "type:incipit",
            f"source_id:source_{source_id}",
            f"work_num_s:{work_num}",
        ],
        "sort": "work_num_ans asc",
        "limit": 1,
    }
    record: Results = await SolrConnection.search(json_request)

    if record.hits == 0:
        return None

    return record.docs[0]


async def handle_incipits_list_request(req, source_id: str) -> Optional[dict]:
    json_request: JsonAPIRequest = {
        "query": "*:*",
        "filter": ["type:source", f"id:source_{source_id}", "has_incipits_b:true"],
    }

    record: Results = await SolrConnection.search(json_request)

    if record.hits == 0:
        return None

    return await IncipitsSection(
        record.docs[0], context={"request": req, "direct_request": True}
    ).data


async def handle_incipit_request(req, source_id: str, work_num: str) -> Optional[dict]:
    incipit_record: Optional[SolrResult] = await _fetch_incipit(source_id, work_num)

    if not incipit_record:
        return None

    return await Incipit(
        incipit_record, context={"request": req, "direct_request": True}
    ).data


async def handle_mei_download(req, source_id: str, work_num: str) -> Optional[dict]:
    """
    Handle MEI file download for a given incipit. Returns a dictionary containing the
    attachment filename and the MEI content sent in the body of the response.
    """
    incipit_record: Optional[SolrResult] = await _fetch_incipit(source_id, work_num)

    if not incipit_record:
        return None

    if "music_incipit_s" not in incipit_record:
        return None

    filename: str = f"rism-source-{source_id}-{work_num}.mei"
    response_headers: dict = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "application/mei+xml",
    }

    mei_content: Optional[str] = render_mei(req, incipit_record)
    if not mei_content:
        return None

    return {"headers": response_headers, "content": mei_content}


async def handle_png_download(req, source_id: str, work_num: str) -> Optional[dict]:
    incipit_record: Optional[SolrResult] = await _fetch_incipit(source_id, work_num)

    if not incipit_record:
        return None

    if "original_pae_sni" not in incipit_record:
        return None

    filename: str = f"rism-source-{source_id}-{work_num}.png"
    response_headers: dict = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "image/png",
    }

    png_content: Optional[bytes] = render_png(req, incipit_record["original_pae_sni"])
    if not png_content:
        return None

    return {"headers": response_headers, "content": png_content}


class IncipitsSection(ypres.AsyncDictSerializer):
    isid = ypres.MethodField(label="id")
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:IncipitsSection")
    part_of = ypres.MethodField(label="partOf")
    items = ypres.MethodField()

    def get_isid(self, obj: SolrResult):
        source_id = re.sub(ID_SUB, "", obj.get("id"))
        req = self.context.get("request")

        return get_identifier(req, "sources.incipits_list", source_id=source_id)

    def get_section_label(self, obj: SolrResult):
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.incipits")

    def get_part_of(self, obj: SolrResult):
        if not self.context.get("direct_request"):
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations
        ident: str = get_identifier(req, "sources.source", source_id=obj.get("id"))

        if "standard_titles_json" not in obj:
            label = {"none": [obj.get("main_title_s", "[No title]")]}
        else:
            label = format_source_label(obj["standard_titles_json"], transl)

        source_type: str = obj.get("source_type_s", "unspecified")
        content_identifiers: list[str] = obj.get("content_types_sm", [])
        record_type: str = obj.get("record_type_s", "item")

        source_types_block = create_source_types_block(
            record_type, source_type, content_identifiers, transl
        )

        return {
            "label": transl.get("records.item_part_of"),
            "source": {
                "id": ident,
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "sourceTypes": source_types_block,
                "label": {"none": [label]},
            },
        }

    async def get_items(self, obj: SolrResult) -> Optional[list]:
        fq: list = [f"source_id:{obj.get('id')}", "type:incipit"]
        sort: str = "work_num_ans asc"
        results: Results = await SolrConnection.search(
            {"query": "*:*", "filter": fq, "sort": sort},
            cursor=True,
            session=self.context.get("session"),
        )

        # It will be strange for this to happen, since we only
        # call this code if the record has said there are incipits
        # for this source. Nevertheless, we'll be safe and return
        # None here.
        if results.hits == 0:
            return None

        return await Incipit(
            results,
            many=True,
            context={
                "request": self.context.get("request"),
                "session": self.context.get("session"),
            },
        ).data


class Incipit(ypres.AsyncDictSerializer):
    incip_id = ypres.MethodField(label="id")
    itype = ypres.StaticField(label="type", value="rism:Incipit")
    label = ypres.MethodField()
    part_of = ypres.MethodField(label="partOf")
    summary = ypres.MethodField()
    rendered = ypres.MethodField()
    encodings = ypres.MethodField()
    properties = ypres.MethodField()

    def get_incip_id(self, obj: dict) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        work_num: str = f"{obj.get('work_num_s')}"

        return get_identifier(
            req, "sources.incipit", source_id=source_id, work_num=work_num
        )

    def get_label(self, obj: SolrResult) -> Optional[dict]:
        label: str = format_incipit_label(obj)

        return {"none": [label]}

    async def get_part_of(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return {
            "label": transl.get(
                "records.item_part_of"
            ),  # TODO: This should probably be changed to 'incipit part of'
            "source": await BaseSource(
                obj, context={"request": req, "session": self.context.get("session")}
            ).data,
        }

    def get_properties(self, obj: SolrResult) -> Optional[dict]:
        # If no notation info in the Solr result, don't bother with this.
        if {"clef_s", "timesig_s", "key_s", "music_incipit_s"}.isdisjoint(obj):
            return None

        d = {
            "clef": obj.get("clef_s"),
            "keysig": obj.get("key_s"),
            "timesig": obj.get("timesig_s"),
            "notation": obj.get("music_incipit_s"),
        }

        return {k: v for k, v in d.items() if v}

    def get_summary(self, obj: SolrResult) -> Optional[list[dict]]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {}

        # Insert the composer only if this is a direct request for the
        # incipit record; otherwise it's embedded. We do this here
        # because otherwise the composer will be added at the end. This
        # way the composer is shown at the start of the block.
        if self.context.get("direct_request"):
            field_config["creator_name_s"] = ("records.composer_author", None)

        field_config.update(
            {
                "titles_sm": ("records.title_movement_tempo", None),
                "text_incipit_sm": ("records.text_incipit", None),
                "key_mode_s": ("records.key_or_mode", key_mode_value_translator),
                "clef_s": ("records.clef", clef_translator),
                "timesig_s": ("records.time_signature", None),
                "role_s": ("records.role", None),
                "scoring_sm": ("records.scoring_in_movement", None),
                "voice_instrument_s": ("records.voice_instrument", None),
                "general_notes_sm": ("records.general_note_incipits", None),
            }
        )

        if (k := obj.get("key_s")) and k != "n":
            field_config.update(
                {
                    "key_s": ("records.key_signature", None),
                }
            )

        return get_display_fields(obj, transl, field_config)

    def get_rendered(self, obj: SolrResult) -> Optional[list]:
        # Use the pre-cached version.
        pae_code: Optional[str] = obj.get("original_pae_sni")
        if not pae_code:
            return None

        req = self.context.get("request")
        is_mensural: bool = obj.get("is_mensural_b", False)

        # Set Verovio to render random IDs for this so that we don't have any ID collisions with
        # search result highlighting
        rendered_pae: Optional[tuple] = render_pae(
            pae_code, use_crc=False, is_mensural=is_mensural
        )

        if not rendered_pae:
            log.error("Could not load music incipit for %s", obj.get("id"))
            return None

        svg, b64midi = rendered_pae

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        work_num: str = obj.get("work_num_s", "")
        png_download_url: str = get_identifier(
            req, "sources.incipit_png_rendering", source_id=source_id, work_num=work_num
        )

        return [
            {"format": "image/svg+xml", "data": svg},
            {"format": "audio/midi", "data": b64midi},
            {"format": "image/png", "url": png_download_url},
        ]

    def get_encodings(self, obj: SolrResult) -> Optional[list]:
        if "music_incipit_s" not in obj:
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        pae_encoding: dict = {}
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        work_num: str = obj.get("work_num_s", "")
        mei_download_url: str = get_identifier(
            req, "sources.incipit_mei_encoding", source_id=source_id, work_num=work_num
        )

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

        return [
            {
                "label": transl.get("records.plaine_and_easie"),
                "format": "application/json",
                "data": pae_encoding,
            },
            {
                "label": {"none": ["MEI"]},
                "format": "application/mei+xml",
                "url": mei_download_url,
            },
        ]
