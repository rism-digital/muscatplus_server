import ypres

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.display_translators import (
    person_gender_translator,
    person_name_variant_labels_translator,
)
from search_server.helpers.identifiers import EXTERNAL_IDS, get_identifier, strip_prefix
from search_server.helpers.solr_connection import SolrResult, result_count
from search_server.resources.people.base_person import BasePerson
from search_server.resources.shared.digital_objects import DigitalObjectsSection
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.relationship import RelationshipsSection
from search_server.resources.sources.works import WorksSection


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
    properties = ypres.MethodField()

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

        person_id = strip_prefix(obj["person_id"])
        return ExternalAuthoritiesSection(
            obj,
            context={
                "request": self.context["request"],
                "route_params": {"person_id": person_id},
                "section_route": "people.person_external_authorities",
                "item_route": "people.person_external_authority",
            },
        ).serialized

    def get_name_variants(self, obj: SolrResult) -> dict | None:
        if "variant_names_json" not in obj:
            return None

        return VariantNamesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    async def get_sources(self, obj: SolrResult) -> dict | None:
        # Do not show a link to sources if this serializer is used for embedded results
        if not self.context.get("direct_request") or obj.get("project_s") in (
            "diamm",
            "cantus",
        ):
            return None

        person_id: str = obj["person_id"]

        # Don't show sources for the anonymous person record.
        if person_id == "person_30004985":
            return None

        fq: list[str] = [
            "type:source",
            f"all_related_people_ids:{person_id}",
        ]
        source_count = await result_count(fq=fq)

        if source_count == 0:
            return None

        ident: str = strip_prefix(person_id)

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
        person_id = strip_prefix(obj["person_id"])
        return RelationshipsSection(
            obj,
            context={
                "request": req,
                "route_params": {"person_id": person_id},
                "section_route": "people.relationships",
                "item_route": "people.relationship",
            },
        ).serialized

    def get_notes(self, obj: SolrResult) -> dict | None:
        person_id = strip_prefix(obj["person_id"])
        notelist: dict = NotesSection(
            obj,
            context={
                "request": self.context["request"],
                "route_params": {"person_id": person_id},
                "section_route": "people.person_notes",
            },
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

    def get_properties(self, obj: SolrResult) -> dict | None:
        authority_links: list[dict] = []
        same_as: list[str] = []
        person_id = strip_prefix(obj["person_id"])

        for ext in obj.get("external_ids", []):
            source, ident = ext.split(":", 1)
            authority_meta = EXTERNAL_IDS.get(source)
            if not authority_meta:
                continue

            link: dict[str, str] = {
                "id": get_identifier(
                    self.context["request"],
                    "people.person_external_authority",
                    person_id=person_id,
                    authority_id=ext,
                ),
                "scheme": source,
                "identifier": ident,
            }
            if uri_tmpl := authority_meta.get("ident"):
                uri = uri_tmpl.format(ident=ident)
                link["uri"] = uri
                same_as.append(uri)

            authority_links.append(link)

        d = {
            "authorityLinks": authority_links,
            "sameAs": same_as,
        }

        return {k: v for k, v in d.items() if v} or None


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
            "authentication_code_s": ("records.authentication_code", None),
            "date_statement_s": ("records.life_dates", None),
            "other_dates_sm": ("records.other_life_dates", None),
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
