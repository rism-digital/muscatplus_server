import logging
import re
from typing import Dict, List, Optional

import pysolr
import serpy

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.identifiers import ID_SUB, get_identifier, get_jsonld_context
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrManager, SolrResult, has_results
from search_server.resources.sources.base_source import BaseSource
from search_server.resources.sources.source_holding import SourceHolding
from search_server.resources.sources.source_incipit import SourceIncipitList
from search_server.resources.sources.source_materialgroup import SourceMaterialGroupList
from search_server.resources.sources.source_note import SourceNoteList
from search_server.resources.sources.source_relationship import SourceRelationshipList, SourceRelationship
from search_server.resources.subjects.subject import Subject

log = logging.getLogger(__name__)


def handle_source_request(req, source_id: str) -> Optional[Dict]:
    fq: List = ["type:source", f"source_id:source_{source_id}"]
    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    source_record = record.docs[0]

    source = FullSource(source_record, context={"request": req,
                                                "direct_request": True})

    return source.data


class SourceItemList(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    sid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[Dict]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "sourceitem_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.items_in_source")


class FullSource(BaseSource):
    summary = serpy.MethodField()
    creator = serpy.MethodField()
    related = serpy.MethodField()
    materials = serpy.MethodField()
    subjects = serpy.MethodField()
    notes = serpy.MethodField()
    holdings = serpy.MethodField()
    incipits = serpy.MethodField()
    see_also = serpy.MethodField(
        label="seeAlso"
    )
    items = serpy.MethodField()

    def get_summary(self, obj: SolrResult) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return get_display_fields(obj, transl)

    def get_creator(self, obj: SolrResult) -> Optional[Dict]:
        fq = [f"source_id:{obj.get('id')}",
              "type:source_person_relationship",
              "relationship_s:cre"]

        res = SolrConnection.search("*:*", fq=fq)

        if res.hits == 0:
            return None

        creator = SourceRelationship(res.docs[0], context={"request": self.context.get('request')})

        return creator.data

    def get_related(self, obj: SolrResult) -> Optional[Dict]:
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:source_person_relationship OR type:source_institution_relationship",
                    "!relationship_s:cre"]

        if not has_results(fq=fq):
            return None

        return SourceRelationshipList(obj, context={"request": self.context.get("request")}).data

    def get_materials(self, obj: SolrResult) -> Optional[Dict]:
        fq: List = ["type:source_materialgroup", f"source_id:{obj.get('source_id')}"]

        if not has_results(fq=fq):
            return None

        return SourceMaterialGroupList(obj, context={"request": self.context.get('request')}).data

    def get_subjects(self, obj: SolrResult) -> Optional[List]:
        subject_ids: Optional[List] = obj.get('subject_ids')
        if not subject_ids:
            return None

        subj_list_q: str = ' OR '.join(subject_ids)

        fq: List = [f"id:({subj_list_q})",
                    "type:subject"]

        if not has_results(fq=fq):
            return None

        sort: str = "term_s asc"

        conn = SolrManager(SolrConnection)
        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        subjects = Subject(conn.results,
                           many=True,
                           context={"request": self.context.get("request")})

        return subjects.data

    def get_notes(self, obj: SolrResult) -> Optional[List]:
        # This does not perform an extra Solr lookup to get the notes, so we can just render it and then
        # look to see if anything came back.
        notelist_obj = SourceNoteList(obj,
                                      context={"request": self.context.get("request")})

        notelist_data = notelist_obj.data

        if notelist_data.get("items"):
            return notelist_data

        return None

    def get_holdings(self, obj: SolrResult) -> Optional[List[Dict]]:
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:holding"]

        if not has_results(fq=fq):
            return None

        sort: str = "siglum_s asc, shelfmark_s asc"

        conn = SolrManager(SolrConnection)
        conn.search("*:*", fq=fq, sort=sort)

        holdings = SourceHolding(conn.results,
                                 many=True, context={"request": self.context.get("request")})

        return holdings.data

    def get_incipits(self, obj: SolrResult) -> Optional[Dict]:
        fq: List = [f"source_id:{obj.get('id')}", "type:source_incipit"]
        if not has_results(fq=fq):
            return None

        return SourceIncipitList(obj, context={"request": self.context.get("request")}).data

    def get_see_also(self, obj: SolrResult) -> Optional[List]:
        pass

    def get_items(self, obj: SolrResult) -> Optional[List]:
        this_id: str = obj.get("source_id")

        # Remember to filter out the current source from the list of all sources in this membership group.
        fq: List = ["type:source", f"source_membership_id:{this_id}", f"!source_id:{this_id}"]
        sort: str = "source_id asc"

        if not has_results(fq=fq):
            return None

        conn = SolrManager(SolrConnection)
        # increasing the number of rows means fewer requests for larger items, but NB: Solr pre-allocates memory
        # for each value in row, so there needs to be a balance between large numbers and fewer requests.
        # (remember that the SolrManager object automatically retrieves the next page of results when iterating)
        conn.search("*:*", fq=fq, sort=sort, rows=100)

        sources = BaseSource(conn.results, many=True,
                             context={"request": self.context.get("request")})

        return sources.data
