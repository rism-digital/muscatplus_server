import re
from typing import Optional

import serpy
from small_asc.client import Results

from search_server.resources.shared.external_link import ExternalResourcesSection
from search_server.resources.shared.relationship import RelationshipsSection
from shared_helpers.display_fields import get_display_fields, LabelConfig
from shared_helpers.display_translators import url_detecting_translator
from shared_helpers.formatters import format_institution_label
from shared_helpers.identifiers import get_identifier, ID_SUB
from shared_helpers.solr_connection import SolrResult, SolrConnection


class ExemplarsSection(serpy.AsyncDictSerializer):
    label = serpy.MethodField()
    stype = serpy.StaticField(
        label="type",
        value="rism:ExemplarsSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.exemplars", {})

    async def get_items(self, obj: SolrResult) -> Optional[dict]:
        # Only select holdings where the institution ID is set. This is due to a buggy import; hopefully we'll
        # be able to remove the institution_id filter clause later... 
        fq: list = [f"source_id:{obj.get('id')}",
                    "type:holding",
                    "institution_id:[* TO *]"]

        sort: str = "siglum_s asc, shelfmark_ans asc"
        results: Results = await SolrConnection.search({
                "query": "*:*",
                "filter": fq,
                "sort": sort
        }, cursor=True)

        if results.hits == 0:
            return None

        return await Exemplar(results,
                              many=True,
                              context={"request": self.context.get("request")}).data


class Exemplar(serpy.AsyncDictSerializer):
    sid = serpy.MethodField(
        label="id"
    )
    stype = serpy.StaticField(
        label="type",
        value="rism:Exemplar"
    )
    label = serpy.MethodField()
    summary = serpy.MethodField()
    notes = serpy.MethodField()
    held_by = serpy.MethodField(
        label="heldBy"
    )
    external_resources = serpy.MethodField(
        label="externalResources"
    )
    relationships = serpy.MethodField()

    def get_sid(self, obj: dict) -> str:
        req = self.context.get('request')
        # find the holding id
        holding_id_val = obj.get("holding_id_sni", "")
        if "-" in holding_id_val:
            holding_id, source_id = obj.get("holding_id_sni").split("-")
        else:
            holding_id = holding_id_val
            source_id = holding_id_val

        return get_identifier(req, "holdings.holding", source_id=source_id, holding_id=holding_id)

    def get_label(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.institution")

    def get_summary(self, obj: SolrResult) -> Optional[list[dict]]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "shelfmark_s": ("records.shelfmark", None),
            "former_shelfmarks_sm": ("records.shelfmark_olim", None),
            "provenance_sm": ("records.provenance", None),
            "material_held_sm": ("records.material_held", None),
            "local_numbers_sm": ("records.local_number", None),
            "acquisition_note_s": ("records.source_of_acquisition_note", None),
            "acquisition_date_s": ("records.date_of_acquisition", None),
            "acquisition_method_s": ("records.method_of_acquisition", None),
            "accession_number_s": ("records.accession_number", None),
            "access_restrictions_sm": ("records.access_restrictions", None),
        }

        return get_display_fields(obj, transl, field_config)

    def get_notes(self, obj: SolrResult) -> Optional[list]:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "general_notes_sm": ("records.general_note", url_detecting_translator),
            "binding_notes_sm": ("records.binding_note", None),
            "bound_with_sm": ("records.bound_with", None),
            "watermark_notes_sm": ("records.watermark_description", None),
            "provenance_notes_sm": ("records.provenance_notes", None)
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_held_by(self, obj: dict) -> Optional[dict]:
        # This should never happen, but it did happen due to a buggy import so we check it first.
        if "institution_id" not in obj:
            return None

        req = self.context.get('request')
        institution_id: str = re.sub(ID_SUB, "", obj.get("institution_id"))

        institution_name: str = format_institution_label(obj)

        return {
            "id": get_identifier(req, "institutions.institution", institution_id=institution_id),
            "type": "rism:Institution",
            "label": {
                "none": [f"{institution_name}"]
            },
        }

    def get_relationships(self, obj: SolrResult) -> Optional[dict]:
        if {'related_people_json', 'related_places_json', 'related_institutions_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")
        return RelationshipsSection(obj, context={"request": req}).data

    def get_external_resources(self, obj: SolrResult) -> Optional[dict]:
        if 'external_resources_json' not in obj:
            return None

        return ExternalResourcesSection(obj, context={"request": self.context.get("request")}).data
