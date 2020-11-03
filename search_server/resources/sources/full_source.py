from typing import Dict, List, Optional

import pysolr
import serpy

from search_server.helpers.solr_connection import SolrConnection, SolrManager
from search_server.resources.sources.base_source import BaseSource
from search_server.resources.sources.source_incipit import SourceIncipit
from search_server.resources.sources.source_materialgroup import SourceMaterialGroupList
from search_server.resources.sources.source_relationship import SourceRelationship
from search_server.resources.sources.source_holding import SourceHolding


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


class FullSource(BaseSource):
    display_fields = serpy.MethodField(
        label="displayFields"
    )
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

    def get_display_fields(self, obj: Dict) -> List[Dict]:
        pass

    def get_related(self, obj: Dict) -> Optional[List[Dict]]:
        conn = SolrManager(SolrConnection)
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:source_person_relationship OR type:source_institution_relationship"]

        conn.search("*:*", fq=fq)

        if conn.hits == 0:
            return None

        relationship = SourceRelationship(conn.results, many=True,
                                          context={"request": self.context.get("request")})

        return relationship.data

    def get_materials(self, obj: Dict) -> Dict:
        grouplist_obj = SourceMaterialGroupList(obj, context={"request": self.context.get('request')})

        return grouplist_obj.data

    def get_subjects(self, obj: Dict) -> List:
        pass

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

        holdings = SourceHolding(conn.results, many=True, context={"request": self.context.get("request")})

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
