import re
from typing import Dict, List, Optional
import logging

import pysolr
import serpy

from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.ld_context import RISM_JSONLD_CONTEXT
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrManager, SolrResult
from search_server.resources.sources.base_source import BaseSource
from search_server.resources.sources.source_creator import SourceCreator
from search_server.resources.sources.source_incipit import SourceIncipit
from search_server.resources.sources.source_materialgroup import SourceMaterialGroupList
from search_server.resources.sources.source_relationship import SourceRelationshipList
from search_server.resources.sources.source_holding import SourceHolding
from search_server.resources.subjects.subject import Subject

log = logging.getLogger(__name__)


def handle_source_request(req, source_id: str) -> Optional[Dict]:
    fq: List = ["type:source", f"source_id:source_{source_id}"]
    fl: str = "*,[child]"
    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, fl=fl, rows=1)

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

    heading = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[Dict]:
        direct_request: bool = self.context.get("direct_request")
        return RISM_JSONLD_CONTEXT if direct_request else None

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "sourceitem_list", source_id=source_id)

    def get_heading(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return {
            "label": transl.get("records.items_in_source")
        }


class FullSource(BaseSource):
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

    def get_creator(self, obj: Dict) -> Optional[Dict]:
        fq = [f"source_id:{obj.get('id')}",
              "type:source_creator"]

        res = SolrConnection.search("*:*", fq=fq)

        if res.hits == 0:
            log.warning("No creator record found for %s", obj.get('id'))
            return None

        creator = SourceCreator(res.docs[0], context={"request": self.context.get('request')})

        return creator.data

    def get_related(self, obj: Dict) -> Dict:
        relationships = SourceRelationshipList(obj,
                                               context={"request": self.context.get("request")})

        return relationships.data

    def get_materials(self, obj: Dict) -> Dict:
        grouplist_obj = SourceMaterialGroupList(obj,
                                                context={"request": self.context.get('request')})

        return grouplist_obj.data

    def get_subjects(self, obj: Dict) -> Optional[List]:
        subject_ids: Optional[List] = obj.get('subject_ids')
        if not subject_ids:
            return None

        subj_list_q: str = ' OR '.join(subject_ids)
        log.debug(subj_list_q)
        fq: List = [f"id:({subj_list_q})",
                    "type:subject"]
        sort: str = "term_s asc"

        conn = SolrManager(SolrConnection)
        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        subjects = Subject(conn.results,
                           many=True,
                           context={"request": self.context.get("request")})

        return subjects.data

    def get_notes(self, obj: Dict) -> List:
        pass

    def get_holdings(self, obj: Dict) -> Optional[List[Dict]]:
        conn = SolrManager(SolrConnection)
        fq: List = [f"source_membership_id:{obj.get('id')}",
                    "type:holding"]
        sort: str = "id asc"

        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        holdings = SourceHolding(conn.results,
                                 many=True, context={"request": self.context.get("request")})

        return holdings.data

    def get_incipits(self, obj: Dict) -> Optional[List[Dict]]:
        conn = SolrManager(SolrConnection)
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:source_incipit"]
        sort: str = "work_num_s asc"

        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        incipits = SourceIncipit(conn.results, many=True,
                                 context={"request": self.context.get("request")})

        return incipits.data

    def get_see_also(self, obj: Dict) -> Optional[List]:
        pass

    def get_items(self, obj: Dict) -> Optional[List]:
        this_id: str = obj.get("source_id")
        conn = SolrManager(SolrConnection)

        # Remember to filter out the current source from the list of all sources in this membership group.
        fq: List = ["type:source", f"source_membership_id:{this_id}", f"!source_id:{this_id}"]
        sort: str = "source_id asc"
        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        sources = BaseSource(conn.results, many=True,
                             context={"request": self.context.get("request")})

        return sources.data
