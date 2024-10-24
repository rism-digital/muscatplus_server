import re
from typing import Callable, Optional

import ypres

from search_server.resources.institutions.base_institution import BaseInstitution
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.relationship import RelationshipsSection
from shared_helpers.display_fields import assemble_label_value
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.languages import merge_language_maps
from shared_helpers.solr_connection import SolrConnection, SolrResult
from shared_helpers.utilities import is_number


async def handle_institution_request(req, institution_id: str) -> Optional[dict]:
    institution_record: Optional[dict] = await SolrConnection.get(
        f"institution_{institution_id}"
    )

    if not institution_record:
        return None

    return await Institution(
        institution_record, context={"request": req, "direct_request": True}
    ).data


class Institution(BaseInstitution):
    location = ypres.MethodField()
    sources = ypres.MethodField()
    external_authorities = ypres.MethodField(label="externalAuthorities")
    relationships = ypres.MethodField()
    notes = ypres.MethodField()
    external_resources = ypres.MethodField(label="externalResources")
    properties = ypres.MethodField()

    def get_sources(self, obj: SolrResult) -> Optional[dict]:
        institution_id = obj["institution_id"]
        ident: str = re.sub(ID_SUB, "", institution_id)
        source_count: int = obj.get("total_sources_i", 0)

        # if no sources are attached OR this is the 's.n.' record, return 0 sources attached.
        if source_count == 0 or ident == "40009305" or obj.get("project_s") == "diamm":
            return None

        return {
            "url": get_identifier(
                self.context.get("request"),
                "institutions.institution_sources",
                institution_id=ident,
            ),
            "totalItems": source_count,
        }

    async def get_location(self, obj: SolrResult) -> Optional[dict]:
        if {
            "street_address_sm",
            "city_address_sm",
            "website_address_sm",
            "email_address_sm",
            "location_loc",
        }.isdisjoint(obj):
            return None

        return LocationAddressSection(
            obj, context={"request": self.context.get("request")}
        ).data

    async def get_external_authorities(self, obj: SolrResult) -> Optional[list[dict]]:
        if "external_ids" not in obj:
            return None

        return ExternalAuthoritiesSection(
            obj["external_ids"], context={"request": self.context.get("request")}
        ).data

    async def get_relationships(self, obj: SolrResult) -> Optional[dict]:
        if not self.context.get("direct_request"):
            return None

        if {
            "related_people_json",
            "related_places_json",
            "related_institutions_json",
            "related_sources_json",
            "now_in_json",
            "contains_json",
        }.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")

        return await RelationshipsSection(obj, context={"request": req}).data

    async def get_notes(self, obj: SolrResult) -> Optional[dict]:
        notes: dict = await NotesSection(
            obj, context={"request": self.context.get("request")}
        ).data
        if "notes" in notes:
            return notes

        return None

    async def get_external_resources(self, obj: SolrResult) -> Optional[dict]:
        if "external_resources_json" not in obj and not obj.get(
            "has_external_record_b", False
        ):
            return None

        return await ExternalResourcesSection(
            obj, context={"request": self.context.get("request")}
        ).data

    def get_properties(self, obj: SolrResult) -> Optional[dict]:
        d = {
            "siglum": obj.get("siglum_s"),
            "countryCodes": obj.get("country_codes_sm", []),
        }

        return {k: v for k, v in d.items() if v} or None


class LocationAddressSection(ypres.DictSerializer):
    ltype = ypres.StaticField(label="type", value="rism:LocationAddressSection")
    label = ypres.MethodField()
    addresses = ypres.MethodField()
    website = ypres.MethodField()
    email = ypres.MethodField()
    coordinates = ypres.MethodField()

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.location_and_address")

    def get_addresses(self, obj: SolrResult) -> Optional[list]:
        if "addresses_json" not in obj:
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        all_addresses = []
        mailing_address_field_config: dict = {
            "street": ("records.street_address", None),
            "city": ("records.city", None),
            "county": ("records.county_province", None),
            "country": ("records.country", None),
            "postcode": ("records.postal_code", None),
            "note": ("records.public_note", None),
        }

        for address in obj.get("addresses_json", []):
            out_addr = {}
            for k, _ in address.items():
                label: tuple[str, Optional[Callable]] = (
                    mailing_address_field_config.get(k, ())
                )
                if not label:
                    continue

                out_addr[k] = assemble_label_value(address, k, label, transl)
            all_addresses.append(out_addr)

        return all_addresses

    def get_coordinates(self, obj: SolrResult) -> Optional[dict]:
        if "location_loc" not in obj:
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        loc: str = obj.get("location_loc")
        lat, lon = loc.split(",")

        if not is_number(lat) or not is_number(lon):
            return None

        institution_id: str = obj["id"]
        ident: str = re.sub(ID_SUB, "", institution_id)

        geojson_uri: str = get_identifier(
            req, "institutions.geo_coordinates", institution_id=ident
        )
        long_label: dict = transl.get("records.longitude")
        lat_label: dict = transl.get("records.latitude")

        lon_lat_label = merge_language_maps(long_label, lat_label)

        return {
            "id": geojson_uri,
            "sectionLabel": transl.get("records.location"),
            "type": "geojson:Feature",
            "geometry": {
                "label": lon_lat_label,
                "type": "geojson:Point",
                "coordinates": [float(lon), float(lat)],
            },
        }

    def get_website(self, obj: SolrResult) -> Optional[dict]:
        if (
            "website_address_sm" not in obj
            or len(obj.get("website_address_sm", [])) == 0
        ):
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return {
            "label": transl.get("general.url"),
            "value": {"none": obj.get("website_address_sm", [])},
        }

    def get_email(self, obj: SolrResult) -> Optional[dict]:
        if "email_address_sm" not in obj or len(obj.get("email_address_sm", [])) == 0:
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return {
            "label": transl.get("general.e_mail"),
            "value": {"none": obj.get("email_address_sm", [])},
        }
