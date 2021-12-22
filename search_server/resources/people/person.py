import logging
import re
from typing import Optional

import serpy

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.solr_connection import SolrResult, SolrConnection
from search_server.resources.people.base_person import BasePerson
from search_server.resources.people.variant_name import VariantNamesSection
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_link import ExternalResourcesSection
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.relationship import RelationshipsSection

log = logging.getLogger()


async def handle_person_request(req, person_id: str) -> Optional[dict]:
    person_record = SolrConnection.get(f"person_{person_id}")

    if not person_record:
        return None

    return Person(person_record, context={"request": req,
                                          "direct_request": True}).data


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

    def get_external_authorities(self, obj: SolrResult) -> Optional[list[dict]]:
        if 'external_ids' not in obj:
            return None

        return ExternalAuthoritiesSection(obj['external_ids'], context={"request": self.context.get("request")}).data

    def get_name_variants(self, obj: SolrResult) -> Optional[list]:
        if 'variant_names_json' not in obj:
            return None

        return VariantNamesSection(obj, context={"request": self.context.get("request")}).data

    def get_sources(self, obj: SolrResult) -> Optional[dict]:
        # Do not show a link to sources if this serializer is used for embedded results
        if not self.context.get("direct_request"):
            return None

        # if no sources are attached to this organization, don't show this section.
        source_count: int = obj.get("source_count_i", 0)
        if source_count == 0:
            return None

        person_id: str = obj.get('person_id')

        # Do not show the list of sources if we're looking at the 'Anonymus' user.
        if person_id == "person_30004985":
            return None

        ident: str = re.sub(ID_SUB, "", person_id)

        return {
            "url": get_identifier(self.context.get("request"), "people.person_sources", person_id=ident),
            "totalItems": obj.get("source_count_i", 0)
        }

    def get_summary(self, obj: SolrResult) -> list[dict]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        field_config: dict = {
            "date_statement_s": ("records.years_birth_death", None),
            "other_dates_s": ("records.other_life_dates", None),
            "gender_s": ("records.gender", None),
            "roles_sm": ("records.profession_or_function", None)
        }

        return get_display_fields(obj, transl, field_config)

    def get_relationships(self, obj: SolrResult) -> Optional[dict]:
        if not self.context.get("direct_request"):
            return None

        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return None.
        if {'related_people_json', 'related_places_json', 'related_institutions_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")
        return RelationshipsSection(obj, context={"request": req}).data

    def get_notes(self, obj: SolrResult) -> Optional[dict]:
        notelist: dict = NotesSection(obj, context={"request": self.context.get("request")}).data

        # Check that the items is not empty; if not, return the note list object.
        if "notes" in notelist:
            return notelist

        return None

    def get_external_resources(self, obj: SolrResult) -> Optional[dict]:
        if 'external_resources_json' not in obj:
            return None

        return ExternalResourcesSection(obj, context={"request": self.context.get("request")}).data

