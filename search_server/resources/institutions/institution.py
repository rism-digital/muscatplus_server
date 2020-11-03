import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.ld_context import RISM_JSONLD_CONTEXT
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrManager
from search_server.resources.institutions.institution_relationship import InstitutionRelationship


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

    label = serpy.MethodField()
    sources = serpy.MethodField()

    def get_ctx(self, obj: Dict) -> Dict:
        direct_request: Optional[bool] = self.context.get("direct_request")
        return RISM_JSONLD_CONTEXT if direct_request else None

    def get_iid(self, obj: Dict) -> str:
        req = self.context.get("request")
        institution_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "institution", institution_id=institution_id)

    def get_label(self, obj: Dict) -> Dict:
        return {"none": [f"{obj.get('name_s')}"]}

    def get_sources(self, obj: Dict) -> Optional[List]:
        conn = SolrManager(SolrConnection)
        fq: List = ["type:source_institution_relationship",
                    f"institution_id:institution_{obj.get('institution_id')}"]

        sort: str = "title_s asc"

        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        sources = InstitutionRelationship(conn.results, many=True,
                                          context={"request": self.context.get("request")})

        return sources.data
