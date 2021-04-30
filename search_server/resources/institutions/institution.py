import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult, result_count
from search_server.resources.shared.external_authority import external_authority_list
# from search_server.resources.shared.institution_relationship import InstitutionRelationshipList
# from search_server.resources.shared.person_relationship import PersonRelationshipList
# from search_server.resources.shared.place_relationship import PlaceRelationshipList


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
    label = serpy.MethodField()
    summary = serpy.MethodField()
    location = serpy.MethodField()
    sources = serpy.MethodField()
    see_also = serpy.MethodField(
        label="seeAlso"
    )
    related = serpy.MethodField()

    def get_iid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        institution_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "institutions.institution", institution_id=institution_id)

    def get_label(self, obj: SolrResult) -> Dict:
        name: str = obj['name_s']

        return {"none": [name]}

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
        institution_id: str = obj.get("institution_id")
        fq: List = ["type:source",
                    f"holding_institution_ids:{institution_id}"]
        num_results: int = result_count(fq=fq)

        if num_results == 0:
            return None

        ident: str = re.sub(ID_SUB, "", institution_id)

        return {
            "id": get_identifier(self.context.get("request"), "institutions.institution_sources", institution_id=ident),
            "totalItems": num_results
        }

    def get_location(self, obj: SolrResult) -> Optional[Dict]:
        loc: str = obj.get("location_loc")
        if not loc:
            return None

        return {
            "type": "geojson:Point",
            "coordinates": loc.split(",")
        }

    def get_see_also(self, obj: SolrResult) -> Optional[List[Dict]]:
        if 'external_ids' not in obj:
            return None

        return external_authority_list(obj['external_ids'])

    def get_related(self, obj: SolrResult) -> Optional[Dict]:
        if not self.context.get("direct_request"):
            return None

        items: List = []

        # if 'related_people_json' in obj:
        #     items.append(
        #         PersonRelationshipList(obj, context={"request": self.context.get("request")}).data
        #     )
        #
        # if 'related_institutions_json' in obj:
        #     items.append(
        #         InstitutionRelationshipList(obj, context={"request": self.context.get("request")}).data
        #     )
        #
        # if 'related_places_json' in obj:
        #     items.append(
        #         PlaceRelationshipList(obj, context={"request": self.context.get("request")}).data
        #     )
        #
        # if not items:
        #     return None
        #
        # req = self.context.get("request")
        # transl: Dict = req.app.ctx.translations
        #
        # return {
        #     "type": "rism:Relations",
        #     "label": transl.get("records.relations"),
        #     "items": items
        # }
