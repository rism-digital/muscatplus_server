from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.identifiers import EXTERNAL_IDS
from search_server.helpers.solr_connection import SolrConnection, SolrManager, SolrResult
from search_server.resources.people.base_person import BasePerson
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


class Person(BasePerson):
    see_also = serpy.MethodField(
        label="seeAlso"
    )
    sources = serpy.MethodField()
    alternate_names = serpy.Field(
        label="alternateNames",
        attr="alternate_names_sm"
    )

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
        # Do not show the list of sources if this serializer is used for embedded results
        if not self.context.get("direct_request"):
            return None

        # Do not show the list of sources if we're looking at the 'Anonymus' user.
        if obj.get("person_id") == "person_30004985":
            return None

        fq: List = ["type:source_person_relationship",
                    f"person_id:{obj.get('person_id')}"]

        sort: str = "main_title_ans asc"
        conn = SolrManager(SolrConnection)

        conn.search("*:*", fq=fq, sort=sort, rows=100)

        if conn.hits == 0:
            return None

        sources = PersonRelationship(conn.results, many=True,
                                     context={"request": self.context.get("request")})

        return sources.data
