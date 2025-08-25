import ypres

from search_server.helpers.display_fields import get_search_result_summary
from search_server.helpers.display_translators import gnd_country_code_labels_translator
from search_server.helpers.formatters import format_institution_label
from search_server.helpers.identifiers import get_identifier, strip_prefix


class InstitutionSearchResult(ypres.DictSerializer):
    srid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    result_type = ypres.StaticField(label="type", value="rism:Institution")
    type_label = ypres.MethodField(label="typeLabel")
    summary = ypres.MethodField()
    flags = ypres.MethodField()

    def get_srid(self, obj: dict) -> str:
        req = self.context["request"]

        id_value: str
        if "project_s" not in obj:
            id_value = strip_prefix(obj["id"])
            return get_identifier(
                req, "institutions.institution", institution_id=id_value
            )

        project: str = obj["project_s"]
        srtype = obj["project_type_s"] if "project_type_s" in obj else obj["type"]
        id_value = strip_prefix(obj["id"])

        return get_identifier(
            req,
            "external.external",
            project=project,
            resource_type=srtype,
            ext_id=id_value,
        )

    def get_slabel(self, obj: dict) -> dict:
        label = format_institution_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl = req.ctx.translations

        return transl.get("records.institution")

    def get_summary(self, obj: dict) -> dict | None:
        field_config: dict = {
            "gnd_country_codes_sm": (
                "countryName",
                "records.country",
                gnd_country_code_labels_translator,
            ),
            "alternate_names_sm": ("otherNames", "records.other_form_of_name", None),
            "total_sources_i": (
                "totalSources",
                "records.sources",
                None,
            ),  # TODO: Find a better label
        }

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_search_result_summary(field_config, transl, obj)

    def get_flags(self, obj: dict) -> dict | None:
        result_flags: dict = {}
        number_of_sources: int = obj.get("total_sources_i", 0)
        linked_with_external_record: bool = obj.get("has_external_record_b", False)
        is_diamm_record: bool = obj.get("project_s") == "diamm"
        is_cantus_record: bool = obj.get("project_s") == "cantus"

        if number_of_sources > 0:
            result_flags.update({"numberOfSources": number_of_sources})

        if linked_with_external_record:
            result_flags.update(
                {"linkedWithExternalRecord": linked_with_external_record}
            )

        if is_diamm_record:
            result_flags.update({"isDIAMMRecord": is_diamm_record})

        if is_cantus_record:
            result_flags.update({"isCantusRecord": is_cantus_record})

        if is_diamm_record or is_cantus_record:
            project_url: str = obj.get("record_uri_sni", "")
            result_flags.update({"externalProjectURL": project_url})

        return result_flags or None
