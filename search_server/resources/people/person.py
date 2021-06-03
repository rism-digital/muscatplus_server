import logging
import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.resources.people.base_person import BasePerson
from search_server.resources.people.name_variant import NameVariantSection
from search_server.resources.people.notes import NotesSection
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_link import ExternalResourcesList
from search_server.resources.shared.relationship import RelationshipsSection

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
    external_authorities = serpy.MethodField(
        label="externalAuthorities"
    )
    summary = serpy.MethodField()
    name_variants = serpy.MethodField(
        label="nameVariants"
    )
    relationships = serpy.MethodField()
    notes = serpy.MethodField(
        label="notes"
    )
    sources = serpy.MethodField()
    external_resources = serpy.MethodField(
        label="externalResources"
    )

    def get_external_authorities(self, obj: SolrResult) -> Optional[List[Dict]]:
        if 'external_ids' not in obj:
            return None

        return ExternalAuthoritiesSection(obj['external_ids'], context={"request": self.context.get("request")}).data

    def get_name_variants(self, obj: SolrResult) -> Optional[List]:
        if 'name_variants_json' not in obj:
            return None

        return NameVariantSection(obj, context={"request": self.context.get("request")}).data

    def get_sources(self, obj: SolrResult) -> Optional[Dict]:
        # Do not show a link to sources if this serializer is used for embedded results
        if not self.context.get("direct_request"):
            return None

        person_id: str = obj.get('person_id')

        # Do not show the list of sources if we're looking at the 'Anonymus' user.
        if person_id == "person_30004985":
            return None

        ident: str = re.sub(ID_SUB, "", person_id)

        return {
            "id": get_identifier(self.context.get("request"), "people.person_sources", person_id=ident),
            "totalItems": obj.get("source_count_i", 0)
        }

    def get_summary(self, obj: SolrResult) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        field_config: Dict = {
            "date_statement_s": ("records.years_birth_death", None),
            "other_dates_s": ("records.other_life_dates", None),
            "gender_s": ("records.gender", None),
            "roles_sm": ("records.profession_or_function", None)
        }

        return get_display_fields(obj, transl, field_config)

    def get_relationships(self, obj: SolrResult) -> Optional[Dict]:
        if not self.context.get("direct_request"):
            return None

        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return None.
        if {'related_people_json', 'related_places_json', 'related_institutions_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")
        return RelationshipsSection(obj, context={"request": req}).data

    def get_notes(self, obj: SolrResult) -> Optional[Dict]:
        notelist: Dict = NotesSection(obj, context={"request": self.context.get("request")}).data

        # Check that the items is not empty; if not, return the note list object.
        if notelist.get("items"):
            return notelist

        return None

    def get_external_resources(self, obj: SolrResult) -> Optional[Dict]:
        if 'external_resources_json' not in obj:
            return None

        return ExternalResourcesList(obj, context={"request": self.context.get("request")}).data

