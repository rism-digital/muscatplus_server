import re
from typing import Optional

import serpy

from shared_helpers.formatters import format_institution_label
from search_server.resources.shared.record_history import get_record_history
from search_server.helpers.display_fields import get_display_fields
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult
from shared_helpers.fields import StaticField
from shared_helpers.serializers import JSONLDContextDictSerializer

SOLR_FIELDS_FOR_BASE_INSTITUTION: list = [
    "id", "type", "created", "updated", "name_s", "city_s", "countries_sm",
    "siglum_s", "alternate_names_sm", "parallel_names_sm", "institution_types_sm", "name_ans"
]


class BaseInstitution(JSONLDContextDictSerializer):
    iid = serpy.MethodField(
        label="id"
    )
    itype = StaticField(
        label="type",
        value="rism:Institution"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    label = serpy.MethodField()
    summary = serpy.MethodField()
    record_history = serpy.MethodField(
        label="recordHistory"
    )

    def get_iid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        institution_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "institutions.institution", institution_id=institution_id)

    def get_label(self, obj: SolrResult) -> dict:
        label: str = format_institution_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.institution")

    def get_summary(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        field_config: dict = {
            "city_s": ("records.city", None),
            "countries_sm": ("records.country", None),
            "siglum_s": ("records.siglum", None),
            "alternate_names_sm": ("records.other_form_of_name", None),
            "parallel_names_sm": ("records.parallel_form", None),
            "institution_types_sm": ("records.type_institution", None)
        }

        return get_display_fields(obj, transl, field_config)

    def get_record_history(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return get_record_history(obj, transl)
