import re
from typing import Optional

import serpy
from small_asc.client import Results

from search_server.helpers.display_translators import url_detecting_translator
from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult, SolrConnection
from search_server.resources.shared.external_link import ExternalResourcesSection
from search_server.resources.shared.relationship import RelationshipsSection


class ExemplarsSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:ExemplarsSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: SolrResult):
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.exemplars")

    def get_items(self, obj: SolrResult) -> Optional[dict]:
        fq: list = [f"source_id:{obj.get('id')}",
                    "type:holding"]

        sort: str = "siglum_s asc, shelfmark_ans asc"
        results: Results = SolrConnection.search({
                "query": "*:*",
                "filter": fq,
                "sort": sort
        }, cursor=True)

        if results.hits == 0:
            return None

        return Exemplar(results,
                        many=True,
                        context={"request": self.context.get("request")}).data


class Exemplar(JSONLDContextDictSerializer):
    # sid = serpy.MethodField(
    #     label="id"
    # )
    stype = StaticField(
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
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "sources.exemplar", source_id=source_id, exemplar_id=obj.get("holding_id_sni"))

    def get_label(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.institution")

    def get_summary(self, obj: SolrResult) -> Optional[list[dict]]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

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
        transl: dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "general_notes_sm": ("records.general_note", url_detecting_translator),
            "binding_notes_sm": ("records.binding_note", None),
            "bound_with_sm": ("records.bound_with", None),
            "watermark_notes_sm": ("records.watermark_description", None),
            "provenance_notes_sm": ("records.provenance_notes", None)
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_held_by(self, obj: dict) -> dict:
        req = self.context.get('request')
        institution_id: str = re.sub(ID_SUB, "", obj.get("institution_id"))

        institution_name: str = obj.get("institution_s")

        if 'department_s' in obj:
            institution_name += f", {obj.get('department_s')}"
        if 'siglum_s' in obj:
            institution_name += f" ({obj['siglum_s']})"

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
