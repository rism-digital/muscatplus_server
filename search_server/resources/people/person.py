import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.identifiers import EXTERNAL_IDS, get_identifier, ID_SUB
from search_server.helpers.solr_connection import SolrConnection, SolrResult, has_results, result_count
from search_server.resources.people.base_person import BasePerson


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
    name_variants = serpy.MethodField(
        label="nameVariants"
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
                "type": source
            })

        return ret

    def get_sources(self, obj: SolrResult) -> Optional[Dict]:
        # Do not show a link to sources this serializer is used for embedded results
        if not self.context.get("direct_request"):
            return None

        person_id: str = obj.get('person_id')

        # Do not show the list of sources if we're looking at the 'Anonymus' user.
        if person_id == "person_30004985":
            return None

        fq: List = ["type:source_person_relationship",
                    f"person_id:{person_id}"]
        num_results: int = result_count(fq=fq)

        if num_results == 0:
            return None

        ident: str = re.sub(ID_SUB, "", person_id)

        return {
            "id": get_identifier(self.context.get("request"), "person_sources", person_id=ident),
            "totalItems": num_results
        }

    def get_name_variants(self, obj: SolrResult) -> Optional[Dict]:
        if not obj.get("name_variants_sm"):
            return None

        req = self.context.get("request")
        transl = req.app.translations

        return {
            "label": transl.get("records.name_variants"),
            "values": {"none": obj.get("name_variants_sm")}
        }
