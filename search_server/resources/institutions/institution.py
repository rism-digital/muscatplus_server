import logging
from collections.abc import Callable

import ypres

from search_server.helpers.display_fields import assemble_label_value
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.languages import merge_language_maps
from search_server.helpers.solr_connection import SolrResult, result_count
from search_server.helpers.utilities import is_number
from search_server.resources.institutions.base_institution import BaseInstitution
from search_server.resources.shared.digital_objects import DigitalObjectsSection
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.relationship import RelationshipsSection

log = logging.getLogger("mp_server")


class Institution(BaseInstitution):
    location = ypres.MethodField()
    sources = ypres.MethodField()
    external_authorities = ypres.MethodField(label="externalAuthorities")
    relationships = ypres.MethodField()
    notes = ypres.MethodField()
    external_resources = ypres.MethodField(label="externalResources")
    digital_objects = ypres.MethodField(label="digitalObjects")
    properties = ypres.MethodField()

    async def get_sources(self, obj: SolrResult) -> dict | None:
        institution_id = obj["institution_id"]
        # if this is the 's.n.' record return 0 sources attached.
        if institution_id == "institution_40009305":
            return None

        source_count: int
        if "total_source_count" in obj:
            # The institution record lookup adds a field to the result that
            # contains the total number of sources attached to this institution
            # as a "total term frequency" value.
            log.info("Using field 'total_source_count' for source count")
            source_count = obj["total_source_count"]
        else:
            # If this serializer is used in places where we can't / don't
            # use the function field, then fall back to a Solr query.
            log.info("Using Solr query for source count")
            fq: list[str] = [
                "type:source",
                f"all_related_institutions_ids:institution_{institution_id}",
            ]
            source_count = await result_count(fq=fq)

        if source_count == 0:
            return None

        ident: str = strip_prefix(institution_id)
        return {
            "url": get_identifier(
                self.context["request"],
                "institutions.institution_sources",
                institution_id=ident,
            ),
            "totalItems": source_count,
        }

    def get_location(self, obj: SolrResult) -> dict | None:
        if {
            "street_address_sm",
            "city_address_sm",
            "website_address_sm",
            "email_address_sm",
            "location_loc",
        }.isdisjoint(obj):
            return None

        return LocationAddressSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    def get_external_authorities(self, obj: SolrResult) -> dict | None:
        if "external_ids" not in obj:
            return None

        return ExternalAuthoritiesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    def get_relationships(self, obj: SolrResult) -> dict | None:
        if not self.context.get("direct_request"):
            return None

        if {
            "related_people_json",
            "related_places_json",
            "related_institutions_json",
            "related_sources_json",
            "now_in_json",
            "contains_json",
            "contributing_projects_json",
        }.isdisjoint(obj.keys()):
            return None

        req = self.context["request"]

        return RelationshipsSection(obj, context={"request": req}).serialized

    def get_notes(self, obj: SolrResult) -> dict | None:
        notes: dict = NotesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

        if "notes" in notes:
            return notes

        return None

    def get_external_resources(self, obj: SolrResult) -> dict | None:
        if "external_resources_json" not in obj and not obj.get(
            "has_external_record_b", False
        ):
            return None

        return ExternalResourcesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    async def get_digital_objects(self, obj: SolrResult) -> dict | None:
        if not obj.get("has_digital_objects_b", False):
            return None

        return await DigitalObjectsSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized

    def get_properties(self, obj: SolrResult) -> dict | None:
        d = {
            "siglum": obj.get("siglum_s"),
            "countryCodes": obj.get("country_codes_sm", []),
            "city": obj.get("city_s"),
        }

        return {k: v for k, v in d.items() if v} or None


class LocationAddressSection(ypres.DictSerializer):
    ltype = ypres.StaticField(label="type", value="rism:LocationAddressSection")
    slabel = ypres.MethodField(label="label")
    addresses = ypres.MethodField()
    website = ypres.MethodField()
    email = ypres.MethodField()
    coordinates = ypres.MethodField()

    def get_slabel(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.location_and_address"]

    def get_addresses(self, obj: SolrResult) -> list | None:
        if "addresses_json" not in obj:
            return None

        req = self.context["request"]
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
                label: tuple[str, Callable | None] = mailing_address_field_config.get(
                    k, ()
                )
                if not label:
                    continue

                out_addr[k] = assemble_label_value(address, k, label, transl)
            all_addresses.append(out_addr)

        return all_addresses

    def get_coordinates(self, obj: SolrResult) -> dict | None:
        if "location_loc" not in obj:
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations

        loc: str = obj["location_loc"]
        lat, lon = loc.split(",")

        if not is_number(lat) or not is_number(lon):
            return None

        institution_id: str = obj["id"]
        ident: str = strip_prefix(institution_id)

        geojson_uri: str = get_identifier(
            req, "institutions.geo_coordinates", institution_id=ident
        )
        long_label: dict = transl["records.longitude"]
        lat_label: dict = transl["records.latitude"]

        lat_lon_label = merge_language_maps(lat_label, long_label)

        return {
            "id": geojson_uri,
            "sectionLabel": transl.get("records.location"),
            "type": "geojson:Feature",
            "geometry": {
                "label": lat_lon_label,
                "type": "geojson:Point",
                # NB: GeoJSON specifies lon,lat, but most people think in
                # lat,lon. Standards, amirite? ¯\_(ツ)_/¯
                "coordinates": [float(lon), float(lat)],
            },
        }

    def get_website(self, obj: SolrResult) -> dict | None:
        if (
            "website_address_sm" not in obj
            or len(obj.get("website_address_sm", [])) == 0
        ):
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return {
            "label": transl.get("general.url"),
            "value": {"none": obj.get("website_address_sm", [])},
        }

    def get_email(self, obj: SolrResult) -> dict | None:
        if "email_address_sm" not in obj or len(obj.get("email_address_sm", [])) == 0:
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return {
            "label": transl.get("general.e_mail"),
            "value": {"none": obj.get("email_address_sm", [])},
        }
