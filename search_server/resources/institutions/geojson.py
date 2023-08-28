from typing import Optional

import ypres

from shared_helpers.formatters import format_institution_label
from shared_helpers.solr_connection import SolrConnection
from shared_helpers.utilities import is_number


async def handle_institution_geojson_request(req, institution_id: str) -> Optional[dict]:
    institution_record: Optional[dict] = await SolrConnection.get(f"institution_{institution_id}")

    if not institution_record:
        return None

    return await InstitutionGeoJson(institution_record, context={"request": req}).data


class InstitutionGeoJson(ypres.AsyncDictSerializer):
    gtype = ypres.StaticField(
        label="type",
        value="FeatureCollection"
    )

    features = ypres.MethodField()

    async def get_features(self, obj: dict) -> Optional[list]:
        primary_obj_id = obj["id"]
        location: Optional[str] = obj.get("location_loc")
        if not location:
            return None

        lat, lon = location.split(",")
        if not is_number(lat) or not is_number(lon):
            return None

        main_org = await GeoJsonFeature(obj, context={"is_primary": True}).data
        if not main_org:
            return None

        all_features: list[dict] = await get_nearby_orgs([lat, lon], primary_obj_id)
        all_features.insert(0, main_org)
        return all_features


async def get_nearby_orgs(coordinates: list, pimary_obj_id: str) -> Optional[list]:
    locval = ",".join(coordinates)
    nearby_orgs_query = {
        "query": "*:*",
        "filter": ["type:institution",
                   "{!geofilt sfield=location_loc}",
                   f"!id:{pimary_obj_id}"],
        "params": {
            "pt": locval,
            "d": 10
        }
    }

    results = await SolrConnection.search(nearby_orgs_query, cursor=True, handler="/query")
    if not results:
        return None

    return await GeoJsonFeature(results, many=True, context={"is_primary": False}).data


class GeoJsonFeature(ypres.AsyncDictSerializer):
    ftype = ypres.StaticField(
        label="type",
        value="Feature"
    )

    properties = ypres.MethodField()
    geometry = ypres.MethodField()

    def get_properties(self, obj: dict) -> dict:
        label: str = format_institution_label(obj)
        orgtypes: list = obj.get("institution_types_sm")
        is_primary: bool = self.context.get("is_primary", False)

        return {
            "name": label,
            "organizationTypes": orgtypes,
            "primary": is_primary
        }

    def get_geometry(self, obj: dict) -> dict:
        location: Optional[str] = obj.get("location_loc")
        if not location:
            return {}

        lat, lon = location.split(",")
        if not is_number(lat) or not is_number(lon):
            return {}

        return {
            "type": "Point",
            "coordinates": [float(lon), float(lat)]
        }
