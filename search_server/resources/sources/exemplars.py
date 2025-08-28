import re

import ypres
from small_asc.client import Results

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import (
    material_content_types_translator,
    material_source_types_translator,
    secondary_literature_json_value_translator,
    url_detecting_translator,
)
from search_server.helpers.formatters import format_institution_label
from search_server.helpers.identifiers import (
    PROJECT_ID_SUB,
    get_identifier,
    strip_prefix,
)
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.resources.shared.digital_objects import DigitalObjectsSection
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.part_of import PartOfSection
from search_server.resources.shared.record_history import get_record_history
from search_server.resources.shared.relationship import RelationshipsSection
from search_server.resources.sources.base_source import BaseSource


class ExemplarsSection(ypres.AsyncDictSerializer):
    eid = ypres.MethodField(label="id")
    etype = ypres.StaticField(label="type", value="rism:ExemplarsSection")
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_eid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        source_holding_id_val: str = obj["id"]

        if "-" in source_holding_id_val:
            source_id_val = source_holding_id_val.split("-")[1]
        else:
            source_id_val = source_holding_id_val

        source_id = strip_prefix(source_id_val)

        return get_identifier(req, "sources.holdings", source_id=source_id)

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl.get("records.exemplars", {})

    async def get_items(self, obj: SolrResult) -> list | None:
        if (
            obj.get("is_contents_record_b", False)
            and obj.get("source_type_s", "") != "manuscript"
        ):
            source_qstmt = f"source_id:{obj.get('source_membership_id')}"
        else:
            source_qstmt = f"source_id:{obj.get('id')}"

        # Only select holdings where the institution ID is set. This is due to a buggy import; hopefully we'll
        # be able to remove the institution_id filter clause later...
        fq: list = [source_qstmt, "type:holding", "institution_id:[* TO *]"]

        sort: str = "siglum_s asc, shelfmark_ans asc"
        results: Results = await SolrConnection.search(
            {"query": "*:*", "filter": fq, "sort": sort, "limit": 100},
            cursor=True,
        )
        if results.hits == 0:
            return None

        return await Holding(
            results,
            many=True,
            context={"request": self.context["request"]},
        ).serialized_many


class Holding(ypres.AsyncDictSerializer):
    sid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="rism:Holding")
    holding_type = ypres.MethodField(label="holdingType")
    section_label = ypres.MethodField(label="sectionLabel")
    hlabel = ypres.MethodField(label="label")
    summary = ypres.MethodField()
    notes = ypres.MethodField()
    held_by = ypres.MethodField(label="heldBy")
    external_resources = ypres.MethodField(label="externalResources")
    relationships = ypres.MethodField()
    bound_with = ypres.MethodField(label="boundWith")
    part_of = ypres.MethodField(label="partOf")
    digital_objects = ypres.MethodField(label="digitalObjects")
    record_history = ypres.MethodField(label="recordHistory")

    def get_sid(self, obj: dict) -> str:
        req = self.context["request"]

        if "project_s" in obj and (proj := obj["project_s"]) == "diamm":
            external_inst_val = obj["external_institution_id"]
            source_id_val = obj["source_id"]

            institution_id = re.sub(PROJECT_ID_SUB, "", external_inst_val)
            source_id = re.sub(PROJECT_ID_SUB, "", source_id_val)

            return get_identifier(
                req,
                "external.external_holding",
                project=proj,
                source_id=source_id,
                institution_id=institution_id,
            )

        source_holding_id_val: str = obj["id"]
        if "-" in source_holding_id_val:
            holding_id_val, source_id_val = source_holding_id_val.split("-")
        else:
            holding_id_val = obj["id"]
            source_id_val = obj["source_id"]

        holding_id = strip_prefix(holding_id_val)
        source_id = strip_prefix(source_id_val)

        return get_identifier(
            req, "sources.holding", source_id=source_id, holding_id=holding_id
        )

    def get_section_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.exemplar"]

    def get_holding_type(self, obj: SolrResult) -> str:
        source_type = obj["source_type_s"]
        match source_type:
            case "manuscript":
                return "rism:ManuscriptHolding"
            case "printed":
                return "rism:PrintHolding"
            case "composite":
                return "rism:CompositeHolding"
            case _:
                return "rism:PrintHolding"

    def get_hlabel(self, obj: SolrResult) -> dict:
        if "holding_titles_json" not in obj:
            return {"none": [obj.get("main_title_s")]}

        holding_titles = obj["holding_titles_json"]

        holding_inst = holding_titles.get("holding_institution")
        holding_siglum = holding_titles.get("holding_siglum")
        holding_shelfmark = holding_titles.get("holding_shelfmark")

        fhinst = f"{holding_inst}" if holding_inst else ""
        fhsigl = f" ({holding_siglum})" if holding_siglum else ""
        fhshel = f", {holding_shelfmark}" if holding_shelfmark else ""

        title = f"{fhinst}{fhsigl}{fhshel}"

        return {"none": [title]}

    def get_summary(self, obj: SolrResult) -> list[dict] | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "material_source_types_sm": (
                "records.source_type",
                material_source_types_translator,
            ),
            "material_content_types_sm": (
                "records.content_type",
                material_content_types_translator,
            ),
            "department_s": ("records.department", None),
            "shelfmark_s": ("records.shelfmark", None),
            "former_shelfmarks_sm": ("records.shelfmark_olim", None),
            "provenance_sm": ("records.provenance", None),
            "material_held_sm": ("records.material_held", None),
            "local_numbers_sm": ("records.local_number", None),
            "format_extent_sm": ("records.format_extent", None),
            "physical_details_sm": ("records.other_physical_details", None),
            "physical_dimensions_sm": ("records.dimensions", None),
            "acquisition_note_s": ("records.source_of_acquisition_note", None),
            "acquisition_date_s": ("records.date_of_acquisition", None),
            "acquisition_method_s": ("records.method_of_acquisition", None),
            "accession_number_s": ("records.accession_number", None),
            "access_restrictions_sm": ("records.access_restrictions", None),
            "bibliographic_references_json": (
                "records.bibliographic_reference",
                secondary_literature_json_value_translator,
            ),
        }

        return get_display_fields(obj, transl, field_config)

    def get_notes(self, obj: SolrResult) -> list | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "general_notes_sm": ("records.general_note", url_detecting_translator),
            "binding_notes_sm": ("records.binding_note", None),
            "bound_with_sm": ("records.bound_with", None),
            "watermark_notes_sm": ("records.watermark_description", None),
            "provenance_notes_sm": ("records.provenance_notes", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_held_by(self, obj: dict) -> dict | None:
        # This should never happen, but it did happen due to a buggy import so we check it first.
        if "institution_id" not in obj:
            return None

        req = self.context["request"]
        institution_id: str
        obj_ident: str

        institution_id = strip_prefix(obj["institution_id"])
        obj_ident = get_identifier(
            req, "institutions.institution", institution_id=institution_id
        )
        institution_name: str = format_institution_label(obj)

        return {
            "id": obj_ident,
            "type": "rism:Institution",
            "label": {"none": [f"{institution_name}"]},
        }

    def get_relationships(self, obj: SolrResult) -> dict | None:
        if {
            "related_people_json",
            "related_places_json",
            "related_institutions_json",
        }.isdisjoint(obj.keys()):
            return None

        req = self.context["request"]
        return RelationshipsSection(
            obj,
            context={
                "request": req,
            },
        ).serialized

    def get_external_resources(self, obj: SolrResult) -> dict | None:
        if "external_resources_json" not in obj:
            return None

        return ExternalResourcesSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized

    async def get_bound_with(self, obj: SolrResult) -> dict | None:
        if "composite_parent_id" not in obj:
            return None

        composite_parent: str = obj["composite_parent_id"]
        source: SolrResult | None = await SolrConnection.get(composite_parent)  # type: ignore
        if not source:
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return {
            "sectionLabel": transl.get("records.bound_with"),
            "source": await BaseSource(
                source, context={"request": self.context["request"]}
            ).serialized,
        }

    def get_part_of(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request", False):
            return None

        return PartOfSection(
            obj, context={"request": self.context["request"]}
        ).serialized
        # return {
        #     "label": transl.get("records.source_details"),
        #     "source": await BaseSource(
        #         obj,
        #         context={
        #             "request": req,
        #         },
        #     ).serialized,
        # }

    async def get_digital_objects(self, obj: SolrResult) -> dict | None:
        if not obj.get("has_digital_objects_b", False):
            return None

        return await DigitalObjectsSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized

    def get_record_history(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request", False):
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)
