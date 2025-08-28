import logging
import re

import ypres
from small_asc.client import Results

from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.helpers.vrv import render_url
from search_server.resources.shared.part_of import PartOfSection

log = logging.getLogger("mp_server")


class DigitalObjectsSection(ypres.AsyncDictSerializer):
    doid = ypres.MethodField(label="id")
    section_label = ypres.MethodField(label="sectionLabel")
    dotype = ypres.StaticField(label="type", value="rism:DigitalObjectsSection")
    items = ypres.MethodField()

    def get_doid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        obj_type: str = obj["type"]
        obj_id: str = re.sub(ID_SUB, "", obj["id"])
        # linked_record_type: str = obj["linked_type_s"]
        # linked_id_val: str = obj["linked_id"]
        # linked_id: str = re.sub(ID_SUB, "", linked_id_val)

        if obj_type == "source":
            return get_identifier(req, "sources.digital_object_list", source_id=obj_id)
        elif obj_type == "person":
            return get_identifier(req, "people.digital_object_list", person_id=obj_id)
        elif obj_type == "holding":
            source_id = re.sub(ID_SUB, "", obj["source_id"])
            return get_identifier(
                req,
                "sources.holding_digital_object_list",
                source_id=source_id,
                holding_id=obj_id,
            )
        elif obj_type == "institution":
            return get_identifier(
                req, "institutions.digital_object_list", institution_id=obj_id
            )
        else:
            log.error("Could not determine ID for %s", obj["id"])
            return "no-id"

    def get_section_label(self, obj: SolrResult):
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl.get("records.digital_objects")

    async def get_items(self, obj: SolrResult) -> list | None:
        fq: list = [f"linked_id:{obj.get('id')}", "type:dobject"]

        results: Results = await SolrConnection.search(
            {"query": "*:*", "filter": fq},
            cursor=True,
        )

        if results.hits == 0:
            return None

        return await DigitalObject(
            results,
            many=True,
            context={
                "request": self.context["request"],
            },
        ).serialized_many


class DigitalObject(ypres.AsyncDictSerializer):
    doid = ypres.MethodField(label="id")
    dotype = ypres.StaticField(label="type", value="rism:DigitalObject")
    part_of = ypres.MethodField(label="partOf")
    slabel = ypres.MethodField(label="label")
    format = ypres.MethodField()
    body = ypres.MethodField()

    def get_doid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        linked_record_type: str = obj["linked_type_s"]
        linked_id_val: str = obj["linked_id"]
        linked_id: str = re.sub(ID_SUB, "", linked_id_val)
        dobject_id_val: str = obj["id"]
        dobject_id: str = re.sub(ID_SUB, "", dobject_id_val)

        if linked_record_type == "source":
            return get_identifier(
                req,
                "sources.digital_object",
                source_id=linked_id,
                dobject_id=dobject_id,
            )
        elif linked_record_type == "person":
            return get_identifier(
                req, "people.digital_object", person_id=linked_id, dobject_id=dobject_id
            )
        elif linked_record_type == "holding":
            # we can get the source ID from the request path.
            source_id: str = req.match_info.get("source_id", "no-id")
            return get_identifier(
                req,
                "sources.holding_digital_object",
                source_id=source_id,
                holding_id=linked_id,
                dobject_id=dobject_id,
            )
        elif linked_record_type == "institution":
            return get_identifier(
                req,
                "institutions.digital_object",
                institution_id=linked_id,
                dobject_id=dobject_id,
            )
        else:
            log.error("Could not determine ID for %s", obj["id"])
            return "no-id"

    def get_slabel(self, obj: SolrResult) -> dict:
        return {"none": [f"{obj.get('description_s')}"]}

    def get_part_of(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request", False):
            return None

        return PartOfSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    def get_format(self, obj: SolrResult) -> str | None:
        return obj["media_type_s"]

    async def get_body(self, obj: SolrResult) -> dict | None:
        d = {}
        mt: str = obj["media_type_s"]
        if mt in ("image/jpeg", "image/png"):
            d.update(
                {
                    "original": {"format": mt, "url": obj.get("original_url_s")},
                    "thumb": {"format": mt, "url": obj.get("thumb_url_s")},
                    "medium": {"format": mt, "url": obj.get("medium_url_s")},
                }
            )
        elif mt == "application/xml":
            mei_url: str = obj["encoding_url_s"]
            svg: str | None = await render_url(mei_url)

            if not svg:
                log.error("Could not render SVG for %s", obj.get("id"))

            d.update(
                {
                    "encoding": {"format": mt, "url": obj.get("encoding_url_s")},
                    "rendered": {"format": "image/svg+xml", "data": svg},
                }
            )
        return d or None
