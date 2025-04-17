import re

import ypres

from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrConnection, SolrResult, result_count


async def handle_subject_request(req, subject_id: str) -> dict | None:
    subject_record: dict | None = await SolrConnection.get(f"subject_{subject_id}")  # type: ignore

    return await Subject(
        subject_record, context={"request": req, "direct_request": True}
    ).serialized


class Subject(ypres.AsyncDictSerializer):
    sid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="rism:Subject")
    slabel = ypres.MethodField(label="label")
    term = ypres.MethodField()
    notes = ypres.MethodField()
    alternate_terms = ypres.MethodField(label="alternateTerms")
    sources = ypres.MethodField()

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        subject_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(req, "subjects.subject", subject_id=subject_id)

    def get_slabel(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl.get("records.subject_heading", {})

    def get_term(self, obj: SolrResult) -> dict:
        return {"none": [obj.get("term_s")]}

    def get_notes(self, obj: SolrResult) -> dict | None:
        # If we're not retrieving the full record with a direct request, do not show the notes
        if not self.context.get("direct_request"):
            return None

        return {"none": [obj.get("notes_sm")]}

    def get_alternate_terms(self, obj: SolrResult) -> dict | None:
        # If we're not retrieving the full record with a direct request, do not show the alternate terms
        if not self.context.get("direct_request"):
            return None

        return {"none": [obj.get("alternate_terms_sm")]}

    async def get_sources(self, obj: SolrResult) -> dict | None:
        # Only give a list of sources for this term if we are looking at a dedicated page for this subject heading, and
        # it is not embedded in another type of record.
        if not self.context.get("direct_request"):
            return None

        subject_id: str = obj["id"]

        fq: list = ["type:source", f"subject_ids:{subject_id}"]
        num_results: int = await result_count(fq=fq)

        if num_results == 0:
            return None

        ident: str = re.sub(ID_SUB, "", subject_id)

        return {
            "id": get_identifier(
                self.context["request"],
                "subjects.subject_sources",
                subject_id=ident,
            ),
            "totalItems": num_results,
        }
