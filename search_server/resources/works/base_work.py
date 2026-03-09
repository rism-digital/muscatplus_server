import ypres

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import (
    key_mode_value_translator,
    title_json_value_translator,
)
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.part_of import PartOfSection
from search_server.resources.shared.record_history import get_record_history
from search_server.resources.shared.relationship import Relationship


class BaseWork(ypres.AsyncDictSerializer):
    wid = ypres.MethodField(label="id")
    wtype = ypres.StaticField(label="type", value="rism:Work")
    slabel = ypres.MethodField(label="label")
    creator = ypres.MethodField()
    summary = ypres.MethodField()
    part_of = ypres.MethodField(label="partOf")
    record_history = ypres.MethodField(label="recordHistory")

    def get_wid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        work_id: str = strip_prefix(obj["id"])

        return get_identifier(req, "works.work", work_id=work_id)

    def get_slabel(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return title_json_value_translator(obj.get("standard_titles_json", []), transl)

    def get_creator(self, obj: SolrResult) -> dict | None:
        if "creator_json" not in obj:
            return None

        return Relationship(
            obj["creator_json"][0],
            context={"request": self.context["request"]},
        ).serialized

    def get_summary(self, obj: SolrResult) -> list[dict] | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "key_mode_s": ("records.key_or_mode", key_mode_value_translator),
            "scoring_summary_sm": ("records.scoring_summary", None),
            "text_incipit_sm": ("records.text_incipit", None),
            "creation_places_sm": ("records.place_of_creation", None),
            "alternative_titles_json": (
                "records.alternative_work_title",
                title_json_value_translator,
            ),
            "date_statement_s": ("records.dates", None),
            "full_rism_id": ("records.rism_id_number", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_part_of(self, obj: SolrResult) -> dict | None:
        if "works_catalogue_json" not in obj:
            return None

        req = self.context["request"]
        return PartOfSection(obj, context={"request": req}).serialized

    def get_record_history(self, obj: SolrResult) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)
