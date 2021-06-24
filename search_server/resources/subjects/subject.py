import re
from typing import Optional, Dict, List

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult, result_count


async def handle_subject_request(req, subject_id: str) -> Optional[Dict]:
    subject_record: Optional[dict] = SolrConnection.get(f"subject_{subject_id}")

    return Subject(subject_record, context={"request": req,
                                            "direct_request": True}).data


class Subject(JSONLDContextDictSerializer):
    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Subject"
    )
    label = serpy.MethodField()
    term = serpy.MethodField()
    notes = serpy.MethodField()
    alternate_terms = serpy.MethodField(
        label="alternateTerms"
    )
    sources = serpy.MethodField()

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        subject_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "subjects.subject", subject_id=subject_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.subject_heading")

    def get_term(self, obj: SolrResult) -> Dict:
        return {"none": [obj.get('term_s')]}

    def get_notes(self, obj: SolrResult) -> Optional[Dict]:
        # If we're not retrieving the full record with a direct request, do not show the notes
        if not self.context.get("direct_request"):
            return None

        return {"none": [obj.get("notes_sm")]}

    def get_alternate_terms(self, obj: SolrResult) -> Optional[Dict]:
        # If we're not retrieving the full record with a direct request, do not show the alternate terms
        if not self.context.get("direct_request"):
            return None

        return {"none": [obj.get("alternate_terms_sm")]}

    async def get_sources(self, obj: SolrResult) -> Optional[Dict]:
        # Only give a list of sources for this term if we are looking at a dedicated page for this subject heading, and
        # it is not embedded in another type of record.
        if not self.context.get("direct_request"):
            return None

        subject_id: str = obj.get("id")

        fq: List = ["type:source",
                    f"subject_ids:{subject_id}"]
        num_results: int = result_count(fq=fq)

        if num_results == 0:
            return None

        ident: str = re.sub(ID_SUB, "", subject_id)

        return {
            "id": get_identifier(self.context.get("request"), "subjects.subject_sources", subject_id=ident),
            "totalItems": num_results
        }
