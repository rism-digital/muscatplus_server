import logging
import re
from typing import Optional

import ypres

from shared_helpers.display_fields import get_display_fields
from shared_helpers.identifiers import get_identifier, ID_SUB
from shared_helpers.solr_connection import SolrResult, SolrConnection
from shared_helpers.display_translators import person_gender_translator
from search_server.resources.people.base_person import BasePerson
from search_server.resources.people.variant_name import VariantNamesSection
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.relationship import RelationshipsSection

log = logging.getLogger("mp_server")


async def handle_person_request(req, person_id: str) -> Optional[dict]:
    person_record = await SolrConnection.get(f"person_{person_id}")

    if not person_record:
        return None

    return await Person(person_record, context={"request": req,
                                                "direct_request": True}).data


class Person(BasePerson):
    biographical_details = ypres.MethodField(
        label="biographicalDetails"
    )
    external_authorities = ypres.MethodField(
        label="externalAuthorities"
    )
    name_variants = ypres.MethodField(
        label="nameVariants"
    )
    relationships = ypres.MethodField()
    notes = ypres.MethodField(
        label="notes"
    )
    sources = ypres.MethodField()
    external_resources = ypres.MethodField(
        label="externalResources"
    )

    def get_biographical_details(self, obj: SolrResult) -> Optional[dict]:
        bio_details: dict = BiographicalDetails(obj, context={"request": self.context.get("request")}).data

        if not bio_details.get("summary"):
            return None

        return bio_details

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
        if not self.context.get("direct_request") or obj.get("project_s") == "diamm":
            return None

        # if no sources are attached to this organization, don't show this section. NB: This will
        # omit the anonymous user since that is manually set to 0 sources.
        source_count: int = obj.get("total_sources_i", 0)
        if source_count == 0:
            return None

        person_id: str = obj['person_id']
        ident: str = re.sub(ID_SUB, "", person_id)

        return {
            "url": get_identifier(self.context.get("request"), "people.person_sources", person_id=ident),
            "totalItems": source_count
        }

    async def get_relationships(self, obj: SolrResult) -> Optional[dict]:
        if not self.context.get("direct_request"):
            return None

        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return None.
        if {'related_people_json',
            'related_places_json',
            'related_institutions_json',
            'related_sources_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")
        return await RelationshipsSection(obj, context={"request": req}).data

    async def get_notes(self, obj: SolrResult) -> Optional[dict]:
        notelist: dict = await NotesSection(obj, context={"request": self.context.get("request")}).data

        # Check that the items is not empty; if not, return the note list object.
        if "notes" in notelist:
            return notelist

        return None

    async def get_external_resources(self, obj: SolrResult) -> Optional[dict]:
        if 'external_resources_json' not in obj and not obj.get("has_external_record_b", False):
            return None

        return await ExternalResourcesSection(obj, context={"request": self.context.get("request")}).data


class BiographicalDetails(ypres.DictSerializer):
    section_label = ypres.MethodField(
        label="sectionLabel"
    )
    summary = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("rism_online.biographical_details")

    def get_summary(self, obj: SolrResult) -> list[dict]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: dict = {
            "date_statement_s": ("records.life_dates", None),
            "other_dates_s": ("records.other_life_dates", None),
            "gender_s": ("records.gender", person_gender_translator),
            "profession_function_sm": ("records.profession_or_function", None)
        }

        return get_display_fields(obj, transl, field_config)
