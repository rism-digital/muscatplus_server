import re

import ypres

from search_server.resources.shared.record_history import get_record_history
from shared_helpers.display_fields import get_display_fields
from shared_helpers.display_translators import country_codes_labels_translator
from shared_helpers.formatters import format_institution_label
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult


class BaseInstitution(ypres.AsyncDictSerializer):
    iid = ypres.MethodField(label="id")
    itype = ypres.StaticField(label="type", value="rism:Institution")
    type_label = ypres.MethodField(label="typeLabel")
    slabel = ypres.MethodField(label="label")
    organization_details = ypres.MethodField(label="organizationDetails")
    record_history = ypres.MethodField(label="recordHistory")

    def get_iid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        institution_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(
            req, "institutions.institution", institution_id=institution_id
        )

    def get_slabel(self, obj: SolrResult) -> dict:
        label: str = format_institution_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.institution"]

    def get_organization_details(self, obj: SolrResult) -> dict | None:
        org_deets: dict = OrganizationDetails(
            obj, context={"request": self.context["request"]}
        ).serialized

        if not org_deets.get("summary"):
            return None

        return org_deets

    def get_record_history(self, obj: dict) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)


class OrganizationDetails(ypres.DictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    summary = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.summary"]

    def get_summary(self, obj: SolrResult) -> list[dict] | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: dict = {
            "siglum_s": ("records.siglum", None),
            "city_s": ("records.city", None),
            "alternate_names_sm": ("records.other_form_of_name", None),
            "parallel_names_sm": ("records.parallel_form", None),
            "institution_types_sm": ("records.type_institution", None),
            "country_codes_sm": ("records.country", country_codes_labels_translator),
            "former_sigla_sm": ("records.former_sigla", None),
            "full_rism_id": ("records.rism_id_number", None),
        }

        return get_display_fields(obj, transl, field_config)
