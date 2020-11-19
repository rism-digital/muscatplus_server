import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, EXTERNAL_IDS, ID_SUB
from search_server.helpers.ld_context import RISM_JSONLD_CONTEXT
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrManager, SolrResult
from search_server.resources.people.person_relationship import PersonRelationship


def handle_person_request(req, person_id: str) -> Optional[Dict]:
    fq: List = ["type:person",
                f"id:person_{person_id}"]

    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    person_record = record.docs[0]
    person = Person(person_record, context={"request": req,
                                            "direct_request": True})

    return person.data


class Person(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    pid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Person"
    )
    name = serpy.MethodField()
    see_also = serpy.MethodField(
        label="seeAlso"
    )
    sources = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[Dict]:
        direct_request: bool = self.context.get("direct_request")
        return RISM_JSONLD_CONTEXT if direct_request else None

    def get_pid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        person_id: str = re.sub(ID_SUB, "", obj.get('id'))

        return get_identifier(req, "person", person_id=person_id)

    def get_name(self, obj: SolrResult) -> Dict:
        name: str = obj.get("name_s")
        dates: Optional[str] = f" ({d})" if (d := obj.get("date_statement_s")) else ""

        return {"none": [f"{name}{dates}"]}

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
            })

        return ret

    def get_sources(self, obj: SolrResult) -> Optional[List]:
        fq: List = ["type:source_person_relationship",
                    f"person_id:{obj.get('person_id')}"]

        sort: str = "title_s asc"
        conn = SolrManager(SolrConnection)

        conn.search("*:*", fq=fq, sort=sort)

        if conn.hits == 0:
            return None

        sources = PersonRelationship(conn.results, many=True,
                                     context={"request": self.context.get("request")})

        return sources.data
