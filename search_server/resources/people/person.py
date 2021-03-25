import logging
import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.identifiers import EXTERNAL_IDS, get_identifier, ID_SUB, PERSON_NAME_VARIANT_TYPES
from search_server.helpers.solr_connection import SolrConnection, SolrResult, result_count
from search_server.resources.people.base_person import BasePerson
from search_server.resources.people.person_institution_relationship import PersonInstitutionRelationshipList
from search_server.resources.people.person_person_relationship import PersonRelationshipList
from search_server.resources.people.person_place_relationship import PersonPlaceRelationshipList

log = logging.getLogger()


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
    summary = serpy.MethodField()
    name_variants = serpy.MethodField(
        label="nameVariants"
    )
    relations = serpy.MethodField()
    sources = serpy.MethodField()

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

    def get_name_variants(self, obj: SolrResult) -> Optional[List]:
        if 'name_variants_json' not in obj:
            return None

        req = self.context.get("request")
        transl: Dict = req.app.translations

        res: List = []
        for variant_type, names in obj.get("name_variants_json").items():
            transl_key = PERSON_NAME_VARIANT_TYPES.get(variant_type)
            res.append({
                "label": transl.get(transl_key),
                "value": names
            })

        return res

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

    def get_summary(self, obj: SolrResult) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        field_config: Dict = {
            "name_variants_sm": ("records.name_variants", None),
            "gender_s": ("records.gender", None)
        }

        return get_display_fields(obj, transl, field_config)

    def get_relations(self, obj: SolrResult) -> Optional[Dict]:
        if not self.context.get("direct_request"):
            return None

        items: List = []

        if 'related_people_json' in obj:
            items.append(
                PersonRelationshipList(obj, context={"request": self.context.get("request")}).data
            )

        if 'related_institutions_json' in obj:
            items.append(
                PersonInstitutionRelationshipList(obj, context={"request": self.context.get("request")}).data
            )

        if "related_places_json" in obj:
            items.append(
                PersonPlaceRelationshipList(obj, context={"request": self.context.get("request")}).data
            )

        # if there are no relationships, return None
        if not items:
            return None

        req = self.context.get("request")
        transl: Dict = req.app.translations

        return {
            "type": "rism:PersonRelations",
            "label": transl.get("records.relations"),
            "items": items
        }

    def get_references(self, obj: SolrResult) -> Optional[Dict]:
        req = self.context.get("request")
        transl = req.app.translations

        return {
            "type": "rism:PersonReferencesNotes",
            "label": transl.get("records.references_and_notes"),
            "items": items
        }