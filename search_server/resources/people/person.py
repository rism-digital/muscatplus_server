import logging
import re

import ypres

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.display_translators import (
    person_gender_translator,
    person_name_variant_labels_translator,
)
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.people.base_person import BasePerson
from search_server.resources.shared.digital_objects import DigitalObjectsSection
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.relationship import RelationshipsSection
from search_server.resources.sources.works import WorksSection

log = logging.getLogger("mp_server")


class Person(BasePerson):
    biographical_details = ypres.MethodField(label="biographicalDetails")
    external_authorities = ypres.MethodField(label="externalAuthorities")
    name_variants = ypres.MethodField(label="nameVariants")
    relationships = ypres.MethodField()
    notes = ypres.MethodField(label="notes")
    sources = ypres.MethodField()
    works = ypres.MethodField()
    external_resources = ypres.MethodField(label="externalResources")
    digital_objects = ypres.MethodField(label="digitalObjects")

    def get_biographical_details(self, obj: SolrResult) -> dict | None:
        bio_details: dict = BiographicalDetails(
            obj, context={"request": self.context["request"]}
        ).serialized

        if not bio_details.get("summary"):
            return None

        return bio_details

    def get_external_authorities(self, obj: SolrResult) -> dict | None:
        if "external_ids" not in obj:
            return None

        return ExternalAuthoritiesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    def get_name_variants(self, obj: SolrResult) -> dict | None:
        if "variant_names_json" not in obj:
            return None

        return VariantNamesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    def get_sources(self, obj: SolrResult) -> dict | None:
        # Do not show a link to sources if this serializer is used for embedded results
        if not self.context.get("direct_request") or obj.get("project_s") == "diamm":
            return None

        # if no sources are attached to this organization, don't show this section. NB: This will
        # omit the anonymous user since that is manually set to 0 sources.
        source_count: int = obj.get("total_sources_i", 0)
        if source_count == 0:
            return None

        person_id: str = obj["person_id"]
        ident: str = re.sub(ID_SUB, "", person_id)

        return {
            "url": get_identifier(
                self.context["request"], "people.person_sources", person_id=ident
            ),
            "totalItems": source_count,
        }

    def get_relationships(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request"):
            return None

        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return None.
        if {
            "related_people_json",
            "related_places_json",
            "related_institutions_json",
            "related_sources_json",
            "contributing_projects_json",
        }.isdisjoint(obj.keys()):
            return None

        req = self.context["request"]
        return RelationshipsSection(obj, context={"request": req}).serialized

    def get_notes(self, obj: SolrResult) -> dict | None:
        notelist: dict = NotesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

        # Check that the items is not empty; if not, return the note list object.
        if "notes" in notelist:
            return notelist

        return None

    def get_works(self, obj: SolrResult) -> dict | None:
        if {"work_nodes_json", "works_catalogue_json"}.isdisjoint(obj.keys()):
            return None

        return WorksSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    def get_external_resources(self, obj: SolrResult) -> dict | None:
        if "external_resources_json" not in obj and not obj.get(
            "has_external_record_b", False
        ):
            return None

        return ExternalResourcesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    async def get_digital_objects(self, obj: SolrResult) -> dict | None:
        if not obj.get("has_digital_objects_b", False):
            return None

        return await DigitalObjectsSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized


class BiographicalDetails(ypres.DictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    summary = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["rism_online.biographical_details"]

    def get_summary(self, obj: SolrResult) -> list[dict] | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: dict = {
            "date_statement_s": ("records.life_dates", None),
            "other_dates_s": ("records.other_life_dates", None),
            "gender_s": ("records.gender", person_gender_translator),
            "profession_function_sm": ("records.profession_or_function", None),
            "full_rism_id": ("records.rism_id_number", None),
        }

        return get_display_fields(obj, transl, field_config)


class VariantNamesSection(ypres.DictSerializer):
    ntype = ypres.StaticField(label="type", value="rism:VariantNamesSection")
    slabel = ypres.MethodField(label="label")
    items = ypres.MethodField()

    def get_slabel(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.name_variants"]

    def get_items(self, obj: SolrResult) -> list[dict]:
        return NameVariant(
            obj["variant_names_json"],
            many=True,
            context={"request": self.context["request"]},
        ).serialized_many


class NameVariant(ypres.DictSerializer):
    vtype = ypres.StaticField(label="type", value="rism:VariantName")
    slabel = ypres.MethodField(label="label")
    value = ypres.MethodField()

    def get_slabel(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return person_name_variant_labels_translator(obj["type"], transl)

    def get_value(self, obj: dict) -> dict:
        return {"none": obj["variants"]}
