import logging
import re
from typing import Optional

import serpy
from small_asc.client import Results

from search_server.helpers.vrv import render_url
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult, SolrConnection

log = logging.getLogger("mp_server")


class DigitalObjectsSection(serpy.AsyncDictSerializer):
    doid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    dotype = serpy.StaticField(
        label="type",
        value="rism:DigitalObjectsSection"
    )
    items = serpy.MethodField()

    def get_doid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        obj_type: str = obj["type"]
        obj_id: str = re.sub(ID_SUB, "", obj["id"])
        # linked_record_type: str = obj["linked_type_s"]
        # linked_id_val: str = obj["linked_id"]
        # linked_id: str = re.sub(ID_SUB, "", linked_id_val)

        if obj_type == "source":
            return get_identifier(req, "sources.digital_object_list", source_id=obj_id)
        elif obj_type == "person":
            return get_identifier(req, "people.digital_object_list", person_id=obj_id)
        elif obj_type == "institution":
            return get_identifier(req, "institution.digital_object_list", institution_id=obj_id)
        else:
            log.error("Could not determine ID for %s", obj["id"])
            return "no-id"

    def get_label(self, obj: SolrResult):
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.digital_objects")

    async def get_items(self, obj: SolrResult) -> Optional[list]:
        fq: list = [f"linked_id:{obj.get('id')}",
                    "type:dobject"]

        results: Results = await SolrConnection.search({"query": "*:*",
                                                        "filter": fq}, cursor=True)

        if results.hits == 0:
            return None

        return await DigitalObject(results,
                                   many=True,
                                   context={"request": self.context.get("request")}).data


class DigitalObject(serpy.AsyncDictSerializer):
    doid = serpy.MethodField(
        label="id"
    )
    dotype = serpy.StaticField(
        label="type",
        value="rism:DigitalObject"
    )
    # part_of = serpy.MethodField(
    #     label="partOf"
    # )
    label = serpy.MethodField()
    format = serpy.MethodField()
    body = serpy.MethodField()

    def get_doid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        linked_record_type: str = obj["linked_type_s"]
        linked_id_val: str = obj["linked_id"]
        linked_id: str = re.sub(ID_SUB, "", linked_id_val)
        dobject_id_val: str = obj["id"]
        dobject_id: str = re.sub(ID_SUB, "", dobject_id_val)

        if linked_record_type == "source":
            return get_identifier(req, "sources.digital_object", source_id=linked_id, dobject_id=dobject_id)
        elif linked_record_type == "person":
            return get_identifier(req, "people.digital_object", person_id=linked_id, dobject_id=dobject_id)
        elif linked_record_type == "institution":
            return get_identifier(req, "institution.digital_object", institution_id=linked_id, dobject_id=dobject_id)
        else:
            log.error("Could not determine ID for %s", obj["id"])
            return "no-id"

    def get_label(self, obj: SolrResult) -> dict:
        return {"none": [f"{obj.get('description_s')}"]}

    def get_part_of(self, obj: SolrResult) -> Optional[dict]:
        # TODO!
        pass

    def get_format(self, obj: SolrResult) -> Optional[str]:
        return obj.get("media_type_s")

    async def get_body(self, obj: SolrResult) -> dict:
        d = {}
        mt: Optional[str] = obj.get("media_type_s")
        if mt in ("image/jpeg", "image/png"):
            d.update({
                "original": {
                    "format": mt,
                    "url": obj.get("original_url_s")
                },
                "thumb": {
                    "format": mt,
                    "url": obj.get("thumb_url_s")
                },
                "medium": {
                    "format": mt,
                    "url": obj.get("medium_url_s")
                }
            })
        elif mt == "application/xml":
            mei_url: str = obj["encoding_url_s"]
            svg: Optional[str] = await render_url(mei_url)

            if not svg:
                log.error("Could not render SVG for %s", obj.get("id"))

            d.update({
                "encoding": {
                    "format": mt,
                    "url": obj.get("encoding_url_s")
                },
                "rendered": {
                    "format": "image/svg+xml",
                    "data": svg
                }
            })

        return d
