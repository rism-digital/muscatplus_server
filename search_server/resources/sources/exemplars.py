import re
from typing import Optional

import ypres
from small_asc.client import Results

from search_server.resources.sources.base_source import BaseSource
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.relationship import RelationshipsSection
from shared_helpers.display_fields import get_display_fields, LabelConfig
from shared_helpers.display_translators import url_detecting_translator, secondary_literature_json_value_translator
from shared_helpers.formatters import format_institution_label
from shared_helpers.identifiers import get_identifier, ID_SUB, PROJECT_ID_SUB, EXTERNAL_IDS
from shared_helpers.solr_connection import SolrResult, SolrConnection


class ExemplarsSection(ypres.AsyncDictSerializer):
    section_label = ypres.MethodField(
        label="sectionLabel"
    )
    items = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.exemplars", {})

    async def get_items(self, obj: SolrResult) -> Optional[dict]:
        # Only select holdings where the institution ID is set. This is due to a buggy import; hopefully we'll
        # be able to remove the institution_id filter clause later...
        if obj.get("is_contents_record_b", False):
            source_qstmt = f"source_id:{obj.get('source_membership_id')}"
        else:
            source_qstmt = f"source_id:{obj.get('id')}"

        fq: list = [source_qstmt,
                    "type:holding",
                    "institution_id:[* TO *]"]

        sort: str = "siglum_s asc, shelfmark_ans asc"
        results: Results = await SolrConnection.search({
                "query": "*:*",
                "filter": fq,
                "sort": sort,
                "limit": 100
            },
            cursor=True,
            session=self.context.get("session"))

        if results.hits == 0:
            return None

        return await Exemplar(results,
                              many=True,
                              context={"request": self.context.get("request"),
                                       "session": self.context.get("session")}).data


class Exemplar(ypres.AsyncDictSerializer):
    sid = ypres.MethodField(
        label="id"
    )
    stype = ypres.StaticField(
        label="type",
        value="rism:Exemplar"
    )
    section_label = ypres.MethodField(
        label="sectionLabel"
    )
    summary = ypres.MethodField()
    notes = ypres.MethodField()
    held_by = ypres.MethodField(
        label="heldBy"
    )
    external_resources = ypres.MethodField(
        label="externalResources"
    )
    relationships = ypres.MethodField()
    bound_with = ypres.MethodField(
        label="boundWith"
    )

    def get_sid(self, obj: dict) -> str:
        req = self.context.get('request')

        if "project_s" in obj and (proj := obj['project_s']) == "diamm":
            external_inst_val = obj["external_institution_id"]
            source_id_val = obj['source_id']

            institution_id = re.sub(PROJECT_ID_SUB, "", external_inst_val)
            source_id = re.sub(PROJECT_ID_SUB, "", source_id_val)

            return get_identifier(req, "external.external_holding",
                                  project=proj,
                                  source_id=source_id,
                                  institution_id=institution_id)

        source_holding_id_val: str = obj['id']
        if "-" in source_holding_id_val:
            holding_id_val, source_id_val = source_holding_id_val.split("-")
        else:
            holding_id_val = obj['id']
            source_id_val = obj['source_id']

        holding_id = re.sub(ID_SUB, "", holding_id_val)
        source_id = re.sub(ID_SUB, "", source_id_val)

        return get_identifier(req, "holdings.holding", source_id=source_id, holding_id=holding_id)

    def get_section_label(self, obj: dict) -> dict:
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
            "bibliographic_references_json": ("records.bibliographic_reference",
                                              secondary_literature_json_value_translator)
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
        institution_id: str
        obj_ident: str

        institution_id = re.sub(ID_SUB, "", obj.get("institution_id", ""))
        obj_ident = get_identifier(req, "institutions.institution", institution_id=institution_id)
        institution_name: str = format_institution_label(obj)

        return {
            "id": obj_ident,
            "type": "rism:Institution",
            "label": {
                "none": [f"{institution_name}"]
            },
        }

    def get_relationships(self, obj: SolrResult) -> Optional[dict]:
        if {'related_people_json', 'related_places_json', 'related_institutions_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")
        return RelationshipsSection(obj, context={"request": req,
                                                  "session": self.context.get("session")}).data

    async def get_external_resources(self, obj: SolrResult) -> Optional[dict]:
        if 'external_resources_json' not in obj:
            return None

        return await ExternalResourcesSection(obj, context={"request": self.context.get("request"),
                                                            "session": self.context.get("session")}).data

    async def get_bound_with(self, obj: SolrResult) -> Optional[dict]:
        if "composite_parent_id" not in obj:
            return None

        composite_parent: str = obj["composite_parent_id"]
        source: Optional[SolrResult] = await SolrConnection.get(composite_parent)
        if not source:
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return {
            "sectionLabel": transl.get("records.bound_with"),
            "source": await BaseSource(source, context={"request": self.context.get("request")}).data
        }
