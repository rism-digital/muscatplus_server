import logging

import ypres
from small_asc.client import Results

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import (
    clef_translator,
    key_mode_value_translator,
)
from search_server.helpers.formatters import format_incipit_label, format_source_label
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.record_types import create_source_types_block
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.helpers.vrv import render_pae
from search_server.resources.sources.base_source import BaseSource
from search_server.resources.works.base_work import BaseWork

log = logging.getLogger("mp_server")


class IncipitsSection(ypres.AsyncDictSerializer):
    isid = ypres.MethodField(label="id")
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:IncipitsSection")
    part_of = ypres.MethodField(label="partOf")
    items = ypres.MethodField()

    def get_isid(self, obj: SolrResult):
        source_id = strip_prefix(obj["id"])
        req = self.context["request"]

        return get_identifier(req, "sources.incipits_list", source_id=source_id)

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.incipits"]

    def get_part_of(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request"):
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations
        ident: str = get_identifier(req, "sources.source", source_id=obj["id"])

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

    async def get_items(self, obj: SolrResult) -> list | None:
        fq: list = [f"source_id:{obj.get('id')}", "type:incipit"]
        sort: str = "work_num_ans asc"
        results: Results = await SolrConnection.search(
            {"query": "*:*", "filter": fq, "sort": sort},
            cursor=True,
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
                "request": self.context["request"],
            },
        ).serialized_many


class WorkIncipitsSection(ypres.AsyncDictSerializer):
    iwid = ypres.MethodField(label="id")
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:WorkIncipitsSection")
    part_of = ypres.MethodField(label="partOf")
    items = ypres.MethodField()

    def get_iwid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        work_id: str = strip_prefix(obj["id"])

        return get_identifier(req, "works.incipits_list", work_id=work_id)

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.incipits"]

    def get_part_of(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request"):
            return None

        req = self.context["request"]
        transl = req.ctx.translations
        ident: str = get_identifier(req, "works.work", work_id=obj["id"])

        return {
            "label": transl["records.item_part_of"],
            "work": {
                "id": ident,
                "type": "rism:Work",
                "typeLabel": transl["records.work"],
                "label": {"none": [obj.get("standard_title_s")]},
            },
        }

    async def get_items(self, obj: SolrResult) -> list | None:
        fq: list = [f"work_id:{obj['id']}", "type:incipit"]
        sort: str = "work_num_ans asc"

        results: Results = await SolrConnection.search(
            {"query": "*:*", "filter": fq, "sort": sort}, cursor=True
        )

        if results.hits == 0:
            return None

        return await Incipit(
            results,
            many=True,
            context={"request": self.context["request"], "direct_request": False},
        ).serialized_many


class Incipit(ypres.AsyncDictSerializer):
    incip_id = ypres.MethodField(label="id")
    itype = ypres.StaticField(label="type", value="rism:Incipit")
    slabel = ypres.MethodField(label="label")
    part_of = ypres.MethodField(label="partOf")
    summary = ypres.MethodField()
    rendered = ypres.MethodField()
    encodings = ypres.MethodField()
    properties = ypres.MethodField()

    def get_incip_id(self, obj: dict) -> str:
        req = self.context["request"]
        parent_type: str = obj["parent_type_s"]
        work_num: str = f"{obj.get('work_num_s')}"

        if parent_type == "work":
            work_id: str = strip_prefix(obj["work_id"])
            return get_identifier(
                req, "works.incipit", work_id=work_id, work_num=work_num
            )

        # assume that it's a source incipit.
        source_id: str = strip_prefix(obj["source_id"])
        return get_identifier(
            req, "sources.incipit", source_id=source_id, work_num=work_num
        )

    def get_slabel(self, obj: SolrResult) -> dict | None:
        label: str = format_incipit_label(obj)

        return {"none": [label]}

    async def get_part_of(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request"):
            return None

        req = self.context["request"]
        parent_type = obj["parent_type_s"]
        transl: dict = req.ctx.translations

        # TODO: This should probably be changed to 'incipit part of'
        d = {
            "label": transl.get("records.item_part_of"),
        }

        if parent_type == "work":
            d["work"] = await BaseWork(obj, context={"request": req}).serialized
        else:
            d["source"] = await BaseSource(obj, context={"request": req}).serialized

        return d

    def get_properties(self, obj: SolrResult) -> dict | None:
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

    def get_summary(self, obj: SolrResult) -> list[dict] | None:
        req = self.context["request"]
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

    def get_rendered(self, obj: SolrResult) -> list | None:
        # Use the pre-cached version.
        parent_type: str = obj["parent_type_s"]

        pae_code: str | None = obj.get("original_pae_sni")
        if not pae_code:
            return None

        req = self.context["request"]
        is_mensural: bool = obj.get("is_mensural_b", False)

        # Set Verovio to render random IDs for this so that we don't have any ID collisions with
        # search result highlighting
        rendered_pae: tuple | None = render_pae(
            pae_code, use_crc=False, is_mensural=is_mensural
        )

        if not rendered_pae:
            log.error("Could not load music incipit for %s", obj.get("id"))
            return None

        svg, b64midi = rendered_pae
        work_num: str = obj.get("work_num_s", "")
        png_download_url: str

        if parent_type == "work":
            work_id: str = strip_prefix(obj["work_id"])
            png_download_url = get_identifier(
                req, "works.incipit_png_rendering", work_id=work_id, work_num=work_num
            )
        else:
            source_id: str = strip_prefix(obj["source_id"])
            png_download_url = get_identifier(
                req,
                "sources.incipit_png_rendering",
                source_id=source_id,
                work_num=work_num,
            )

        return [
            {"format": "image/svg+xml", "data": svg},
            {"format": "audio/midi", "data": b64midi},
            {"format": "image/png", "url": png_download_url},
        ]

    def get_encodings(self, obj: SolrResult) -> list | None:
        if "music_incipit_s" not in obj:
            return None

        req = self.context["request"]
        parent_type = obj["parent_type_s"]
        transl: dict = req.ctx.translations

        pae_encoding: dict = {}
        work_num: str = obj.get("work_num_s", "")
        mei_download_url: str

        if parent_type == "work":
            work_id: str = strip_prefix(obj["work_id"])
            mei_download_url = get_identifier(
                req, "works.incipit_mei_encoding", work_id=work_id, work_num=work_num
            )
        else:
            source_id: str = strip_prefix(obj["source_id"])
            mei_download_url = get_identifier(
                req,
                "sources.incipit_mei_encoding",
                source_id=source_id,
                work_num=work_num,
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
