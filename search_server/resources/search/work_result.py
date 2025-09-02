import ypres

from search_server.helpers.display_fields import get_search_result_summary
from search_server.helpers.display_translators import key_mode_value_translator
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.languages import add_to_each_translation, choose_plural
from search_server.helpers.solr_connection import SolrResult
from search_server.helpers.vrv import render_pae


class WorkSearchResult(ypres.DictSerializer):
    srid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    result_type = ypres.StaticField(label="type", value="rism:Work")
    type_label = ypres.MethodField(label="typeLabel")
    # part_of = ypres.MethodField(label="partOf")
    summary = ypres.MethodField()
    flags = ypres.MethodField()
    rendered = ypres.MethodField()
    sources = ypres.MethodField()

    def get_srid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        work_id = obj["rism_id"]
        return get_identifier(req, "works.work", work_id=work_id)

    def get_slabel(self, obj: SolrResult) -> dict:
        return {"none": [f"{obj['standard_title_s']}"]}

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl = req.ctx.translations

        return transl.get("records.work")

    # TBD if this is needed.
    # def get_part_of(self, obj: SolrResult) -> dict | None:
    #     if "works_catalogue_json" not in obj:
    #         return None
    #
    #     return PartOfSection(
    #         obj, context={"request": self.context["request"]}
    #     ).serialized

    def get_summary(self, obj: SolrResult) -> dict | None:
        field_config: dict = {
            "key_mode_s": ("keyMode", "records.key_or_mode", key_mode_value_translator),
            "text_incipit_sm": ("textIncipit", "records.text_incipit", None),
        }

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_search_result_summary(field_config, transl, obj)

    def get_flags(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        flags: dict = {}

        catalogue_code = obj.get("catalogue_s")
        catalogue_number = obj.get("number_page_s")
        if catalogue_code and catalogue_number:
            flags["catalogNumber"] = f"{catalogue_code} {catalogue_number}"

        number_of_sources: int = obj.get("source_count_i", 0)
        flags.update({"numberOfSources": number_of_sources})

        key_mode: str | None = obj.get("key_mode_s")
        if key_mode:
            key_mode_vals = key_mode_value_translator(key_mode, transl)
            flags["keyMode"] = key_mode_vals

        scoring: list[str] | None = obj.get("scoring_summary_sm")
        if scoring:
            flags["scoringSummary"] = "; ".join(scoring)

        return flags

    def get_rendered(self, obj: SolrResult) -> dict | None:
        if not obj.get("has_notation_b", False):
            return None

        pae_code: str | None = obj.get("original_pae_sni")
        if not pae_code:
            return None

        is_mensural: bool = obj.get("is_mensural_b", False)

        svg, _ = render_pae(
            pae_code, is_mensural=is_mensural, hard_truncate=True, enlarged=True
        )

        if not svg:
            return None

        return {"format": "image/svg+xml", "data": svg}

    def get_sources(self, obj: SolrResult) -> dict | None:
        number_of_sources: int = obj.get("source_count_i", 0)
        if number_of_sources == 0:
            return None

        translated_label_key = choose_plural(
            "records.source", "records.sources", number_of_sources
        )
        req = self.context["request"]
        transl: dict = req.ctx.translations
        translation: dict = transl.get(translated_label_key, {})
        numval = f"{number_of_sources} "  # NB: The space at the end is important!
        adjusted_translations = add_to_each_translation(translation, numval)

        work_id = strip_prefix(obj["id"])
        sources_url = get_identifier(req, "works.work_sources", work_id=work_id)
        return {"label": adjusted_translations, "url": sources_url}
