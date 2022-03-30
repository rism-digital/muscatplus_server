import re
from typing import Optional

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.identifiers import get_identifier, ID_SUB
from search_server.helpers.solr_connection import SolrResult, SolrConnection
from search_server.resources.institutions.base_institution import BaseInstitution
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_link import ExternalResourcesSection
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.relationship import RelationshipsSection


async def handle_institution_request(req, institution_id: str) -> Optional[dict]:
    institution_record: Optional[dict] = SolrConnection.get(f"institution_{institution_id}")

    if not institution_record:
        return None

    return Institution(institution_record, context={"request": req,
                                                    "direct_request": True}).data


class Institution(BaseInstitution):
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

    def get_sources(self, obj: SolrResult) -> Optional[dict]:
        source_count: int = obj.get("source_count_i", 0)
        if source_count == 0:
            return None

        institution_id: str = obj.get("institution_id")
        ident: str = re.sub(ID_SUB, "", institution_id)

        return {
            "url": get_identifier(self.context.get("request"), "institutions.institution_sources", institution_id=ident),
            "totalItems": source_count
        }

    def get_location(self, obj: SolrResult) -> Optional[dict]:
        if {"street_address_sm", "city_address_sm", "website_address_sm", "email_address_sm", "location_loc"}.isdisjoint(obj):
            return None

        return LocationAddressSection(obj, context={"request": self.context.get("request")}).data

    def get_external_authorities(self, obj: SolrResult) -> Optional[list[dict]]:
        if 'external_ids' not in obj:
            return None

        return ExternalAuthoritiesSection(obj['external_ids'], context={"request": self.context.get("request")}).data

    def get_relationships(self, obj: SolrResult) -> Optional[dict]:
        if not self.context.get("direct_request"):
            return None

        if {'related_people_json', 'related_places_json', 'related_institutions_json', 'now_in_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")

        return RelationshipsSection(obj, context={"request": req}).data

    def get_notes(self, obj: SolrResult) -> Optional[dict]:
        notes: dict = NotesSection(obj, context={"request": self.context.get("request")}).data
        if 'notes' in notes:
            return notes

        return None

    def get_external_resources(self, obj: SolrResult) -> Optional[dict]:
        if 'external_resources_json' not in obj:
            return None

        return ExternalResourcesSection(obj, context={"request": self.context.get("request")}).data


class LocationAddressSection(ContextDictSerializer):
    ltype = StaticField(
        label="type",
        value="rism:LocationAddressSection"
    )
    label = serpy.MethodField()
    mailing_address = serpy.MethodField(
        label="mailingAddress"
    )
    website = serpy.MethodField()
    email = serpy.MethodField()
    coordinates = serpy.MethodField()

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.location_and_address")

    def get_mailing_address(self, obj: SolrResult) -> Optional[dict]:
        if "street_address_sm" not in obj:
            return None

        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        mailing_address_field_config: dict = {
            "street_address_sm": ("records.street_address", None),
            "city_address_sm": ("records.city", None),
            "country_address_sm": ("records.country", None),
            "postcode_address_sm": ("records.postal_code", None),
            "public_note_address_sm": ("records.public_note", None)
        }
        return get_display_fields(obj, transl, mailing_address_field_config)

    def get_coordinates(self, obj: SolrResult) -> Optional[dict]:
        if "location_loc" not in obj:
            return None

        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        loc: str = obj.get("location_loc")

        return {
            "label": transl.get("records.location"),
            "geometry": {
                "type": "geojson:Point",
                "coordinates": loc.split(",")
            }
        }

    def get_website(self, obj: SolrResult) -> Optional[dict]:
        if "website_address_sm" not in obj or len(obj.get("website_address_sm", [])) == 0:
            return None

        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return {
            "label": transl.get("general.url"),
            "value": obj.get("website_address_sm")[0]
        }

    def get_email(self, obj: SolrResult) -> Optional[dict]:
        if "email_address_sm" not in obj or len(obj.get("email_address_sm", [])) == 0:
            return None

        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return {
            "label": transl.get("general.e_mail"),
            "value": obj.get("email_address_sm")[0]
        }

