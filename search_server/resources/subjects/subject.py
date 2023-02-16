import re
from typing import Optional

import serpy

from shared_helpers.identifiers import get_identifier, ID_SUB
from shared_helpers.serializers import JSONLDAsyncDictSerializer
from shared_helpers.solr_connection import SolrConnection, SolrResult, result_count


async def handle_subject_request(req, subject_id: str) -> Optional[dict]:
    subject_record: Optional[dict] = await SolrConnection.get(f"subject_{subject_id}")

    return await Subject(subject_record, context={"request": req,
                                                  "direct_request": True}).data


class Subject(JSONLDAsyncDictSerializer):
    sid = serpy.MethodField(
        label="id"
    )
    stype = serpy.StaticField(
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
        subject_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(req, "subjects.subject", subject_id=subject_id)

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.subject_heading", {})

    def get_term(self, obj: SolrResult) -> dict:
        return {"none": [obj.get('term_s')]}

    def get_notes(self, obj: SolrResult) -> Optional[dict]:
        # If we're not retrieving the full record with a direct request, do not show the notes
        if not self.context.get("direct_request"):
            return None

        return {"none": [obj.get("notes_sm")]}

    def get_alternate_terms(self, obj: SolrResult) -> Optional[dict]:
        # If we're not retrieving the full record with a direct request, do not show the alternate terms
        if not self.context.get("direct_request"):
            return None

        return {"none": [obj.get("alternate_terms_sm")]}

    async def get_sources(self, obj: SolrResult) -> Optional[dict]:
        # Only give a list of sources for this term if we are looking at a dedicated page for this subject heading, and
        # it is not embedded in another type of record.
        if not self.context.get("direct_request"):
            return None

        subject_id: str = obj["id"]

        fq: list = ["type:source",
                    f"subject_ids:{subject_id}"]
        num_results: int = await result_count(fq=fq)

        if num_results == 0:
            return None

        ident: str = re.sub(ID_SUB, "", subject_id)

        return {
            "id": get_identifier(self.context.get("request"), "subjects.subject_sources", subject_id=ident),
            "totalItems": num_results
        }
