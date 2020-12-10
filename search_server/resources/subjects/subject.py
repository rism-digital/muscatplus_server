import re
from typing import Optional, Dict, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, ID_SUB, RISM_JSONLD_CONTEXT, get_jsonld_context, \
    JSONLDContext
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult, SolrConnection, SolrManager, result_count
from search_server.resources.sources.base_source import BaseSource


def handle_subject_request(req, subject_id: str) -> Optional[Dict]:
    fq: List = [
        "type:subject",
        f"id:subject_{subject_id}"
    ]
    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    subject_record = record.docs[0]
    subject = Subject(subject_record, context={"request": req,
                                               "direct_request": True})

    return subject.data


class Subject(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Subject"
    )
    label = serpy.MethodField()
    term = serpy.StrField(
        attr="term_s"
    )
    notes = serpy.MethodField()
    alternate_terms = serpy.MethodField(
        label="alternateTerms"
    )
    sources = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[JSONLDContext]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        subject_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "subject", subject_id=subject_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.subject_heading")

    def get_notes(self, obj: SolrResult) -> Optional[List]:
        direct_request: bool = self.context.get("direct_request")

        # If we're not retrieving the full record with a direct request, do not show the notes
        if not direct_request:
            return None

        return obj.get("notes_sm")

    def get_alternate_terms(self, obj: SolrResult) -> Optional[List]:
        direct_request: bool = self.context.get("direct_request")

        # If we're not retrieving the full record with a direct request, do not show the alternate terms
        if not direct_request:
            return None

        return obj.get("alternate_terms_sm")

    def get_sources(self, obj: SolrResult) -> Optional[Dict]:
        # Only give a list of sources for this term if we are looking at a dedicated page for this subject heading, and
        # it is not embedded in another type of record.
        direct_request: bool = self.context.get("direct_request")

        if not direct_request:
            return None

        subject_id: str = obj.get("id")

        fq: List = ["type:source",
                    f"subject_ids:{subject_id}"]
        num_results: int = result_count(fq=fq)

        if num_results == 0:
            return None

        ident: str = re.sub(ID_SUB, "", subject_id)

        return {
            "id": get_identifier(self.context.get("request"), "subject_sources", subject_id=ident),
            "totalItems": num_results
        }
