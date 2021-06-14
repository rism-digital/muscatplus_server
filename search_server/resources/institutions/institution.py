import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_link import ExternalResourcesSection
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.relationship import RelationshipsSection


def handle_institution_request(req, institution_id: str) -> Optional[Dict]:
    fq: List = ["type:institution",
                f"id:institution_{institution_id}"]

    record: pysolr.Results = SolrConnection.search("*:*", fq=fq)

    if record.hits == 0:
        return None

    institution_record = record.docs[0]
    institution = Institution(institution_record, context={"request": req,
                                                           "direct_request": True})

    return institution.data


class Institution(JSONLDContextDictSerializer):
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
    location = serpy.MethodField()
    sources = serpy.MethodField()
    external_authorities = serpy.MethodField(
        label="externalAuthorities"
    )
    relationships = serpy.MethodField()
    notes = serpy.MethodField()
    external_resources = serpy.MethodField(
        label="externalResources"
    )

    def get_iid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        institution_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "institutions.institution", institution_id=institution_id)

    def get_label(self, obj: SolrResult) -> Dict:
        name: str = obj['name_s']

        return {"none": [name]}

    def get_type_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.institution")

    def get_summary(self, obj: SolrResult) -> Optional[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        field_config: Dict = {
            "siglum_s": ("records.siglum", None),
            "alternate_names_sm": ("records.other_form_of_name", None),
            "institution_types_sm": ("records.type_institution", None)
        }

        return get_display_fields(obj, transl, field_config)

    def get_sources(self, obj: SolrResult) -> Optional[Dict]:
        source_count: int = obj.get("source_count_i", 0)
        if source_count == 0:
            return None

        institution_id: str = obj.get("institution_id")
        ident: str = re.sub(ID_SUB, "", institution_id)

        return {
            "url": get_identifier(self.context.get("request"), "institutions.institution_sources", institution_id=ident),
            "totalItems": source_count
        }

    def get_location(self, obj: SolrResult) -> Optional[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        loc: str = obj.get("location_loc")
        if not loc:
            return None

        return {
            "label": transl.get("records.location"),
            "type": "geojson:Point",
            "coordinates": loc.split(",")
        }

    def get_external_authorities(self, obj: SolrResult) -> Optional[List[Dict]]:
        if 'external_ids' not in obj:
            return None

        return ExternalAuthoritiesSection(obj['external_ids'], context={"request": self.context.get("request")}).data

    def get_relationships(self, obj: SolrResult) -> Optional[Dict]:
        if not self.context.get("direct_request"):
            return None

        if {'related_people_json', 'related_places_json', 'related_institutions_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")

        return RelationshipsSection(obj, context={"request": req}).data

    def get_notes(self, obj: SolrResult) -> Optional[Dict]:
        notes: Dict = NotesSection(obj, context={"request": self.context.get("request")}).data
        if 'notes' in notes:
            return notes

        return None

    def get_external_resources(self, obj: SolrResult) -> Optional[Dict]:
        if 'external_resources_json' not in obj:
            return None

        return ExternalResourcesSection(obj, context={"request": self.context.get("request")}).data