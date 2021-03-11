import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField, LanguageMapField
from search_server.helpers.identifiers import get_identifier, ID_SUB, get_jsonld_context, \
    JSONLDContext, EXTERNAL_IDS
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult, result_count


def handle_institution_request(req, institution_id: str) -> Optional[Dict]:
    fq: List = ["type:institution",
                f"id:institution_{institution_id}"]

    record: pysolr.Results = SolrConnection.search("*:*", fq=fq)

    if record.hits == 0:
        return None

    institution_record = record.docs[0]
    institution = Institution(institution_record, context={"request": req,
                                                           "direct_request": True})

    return institution.data


class Institution(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    iid = serpy.MethodField(
        label="id"
    )
    itype = StaticField(
        label="type",
        value="rism:Institution"
    )
    label = LanguageMapField(
        attr="name_s"
    )
    other_names = LanguageMapField(
        label="otherNames",
        attr="alternate_names_sm",
        required=False
    )
    location = serpy.MethodField()
    sources = serpy.MethodField()
    see_also = serpy.MethodField(
        label="seeAlso"
    )
    siglum = LanguageMapField(
        attr="siglum_s",
        required=False
    )

    def get_ctx(self, obj: SolrResult) -> Optional[JSONLDContext]:
        direct_request: Optional[bool] = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_iid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        institution_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "institution", institution_id=institution_id)

    def get_sources(self, obj: SolrResult) -> Optional[Dict]:
        institution_id: str = obj.get("institution_id")
        fq: List = ["type:source",
                    f"holding_institution_ids:{institution_id}"]
        num_results: int = result_count(fq=fq)

        if num_results == 0:
            return None

        ident: str = re.sub(ID_SUB, "", institution_id)

        return {
            "id": get_identifier(self.context.get("request"), "institution_sources", institution_id=ident),
            "totalItems": num_results
        }

    def get_location(self, obj: SolrResult) -> Optional[Dict]:
        loc: str = obj.get("location_loc")
        if not loc:
            return None

        return {
            "type": "geojson:Point",
            "coordinates": loc.split(",")
        }

    def get_see_also(self, obj: SolrResult) -> Optional[List[Dict]]:
        external_ids: Optional[List] = obj.get("external_ids")
        if not external_ids:
            return None

        ret: List = []
        for ext in external_ids:
            source, ident = ext.split(":")
            base = EXTERNAL_IDS.get(source)
            if not base:
                continue

            ret.append({
                "id": base.format(ident=ident),
                "type": source
            })

        return ret
