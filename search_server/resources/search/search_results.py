import logging
import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import (
    get_identifier,
    ID_SUB
)
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.search.base_search import BaseSearchResults


log = logging.getLogger(__name__)


class SearchResults(BaseSearchResults):
    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        results: List[Dict] = []
        req = self.context.get('request')

        for d in obj.docs:
            if d['type'] == "source":
                results.append(SourceSearchResult(d, context={"request": req}).data)
            elif d['type'] == "person":
                results.append(PersonSearchResult(d, context={"request": req}).data)
            elif d['type'] == "institution":
                results.append(InstitutionSearchResult(d, context={"request": req}).data)
            elif d['type'] == 'place':
                results.append(PlaceSearchResult(d, context={"request": req}).data)
            elif d['type'] == "liturgical_festival":
                results.append(LiturgicalFestivalSearchResult(d, context={"request": req}).data)
            elif d['type'] == "incipit":
                results.append(IncipitSearchResult(d, context={"request": req}).data)
            else:
                return None

        return results


class SourceSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Source"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    summary = serpy.MethodField()
    part_of = serpy.MethodField(
        label="partOf"
    )
    flags = serpy.MethodField()

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "sources.source", source_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label: str = obj.get("main_title_s")

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations
        return transl.get("records.source")

    def get_summary(self, obj: Dict) -> Optional[List[Dict]]:
        field_config: LabelConfig = {
            "creator_name_s": ("records.composer_author", None),
            "source_type_sm": ("records.source_type", None),  # TODO: The value of this field should be translatable
        }

        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return get_display_fields(obj, transl, field_config=field_config)

    def get_part_of(self, obj: SolrResult) -> Optional[Dict]:
        """
            Provides a pointer back to a parent. Used for Items in Sources and Incipits.
        """
        is_item: bool = obj.get('is_item_record_b', False)
        # if it isn't an item record, then it isn't part of anything!
        if not is_item:
            return None

        req = self.context.get("request")

        parent_title: str
        parent_source_id: str

        parent_title = obj.get("source_membership_title_s")
        parent_source_id = re.sub(ID_SUB, "", obj.get("source_membership_id"))

        transl: Dict = req.app.ctx.translations

        return {
            "label": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": get_identifier(req, "sources.source", source_id=parent_source_id),
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "label": {"none": [parent_title]}
            }
        }

    def get_flags(self, obj: Dict) -> Optional[Dict]:
        has_digitization: bool = obj.get("has_digitization_b", False)
        is_item: bool = obj.get("is_item_record_b", False)
        has_incipits: bool = obj.get("has_incipits_b", False)
        has_iiif: bool = obj.get("has_iiif_manifest_b", False)
        flags: Dict = {}

        if has_digitization:
            flags.update({"hasDigitization": has_digitization})

        if is_item:
            flags.update({"isItem": is_item})

        if has_incipits:
            flags.update({"hasIncipits": has_incipits})

        if has_iiif:
            flags.update({"hasIIIFManifest": has_iiif})

        # return None if flags are empty.
        return flags or None


class PersonSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Person"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    summary = serpy.MethodField()

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "people.person", person_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label: str = _format_person_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.person")

    def get_summary(self, obj: Dict) -> Optional[List[Dict]]:
        field_config = {
            "roles_sm": ("records.profession_or_function", None)
        }

        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return get_display_fields(obj, transl, field_config=field_config)


class InstitutionSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Institution"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "institutions.institution", institution_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label = _format_institution_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.institution")


class PlaceSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Place"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "places.place", place_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label: str = obj.get("FIXME")

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.place")


class LiturgicalFestivalSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:LiturgicalFestival"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "festivals.festival", festival_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label: str = obj.get("name_s")

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.liturgical_festival")


class IncipitSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Incipit"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    part_of = serpy.MethodField(
        label="partOf"
    )

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "incipits.incipit", incipit_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label: str = _format_incipit_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.incipit")

    def get_part_of(self, obj: SolrResult) -> Optional[Dict]:
        """
            Provides a pointer back to the parent for this incipit
        """
        req = self.context.get("request")
        parent_title: str
        parent_source_id: str

        parent_title: str = obj.get("source_title_s")
        parent_source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        transl: Dict = req.app.ctx.translations

        return {
            "label": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": get_identifier(req, "sources.source", source_id=parent_source_id),
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "label": {"none": [parent_title]}
            }
        }


def _format_institution_label(obj: Dict) -> str:
    city = siglum = ""

    if 'city_s' in obj:
        city = f", {obj['city_s']}"
    if 'siglum_s' in obj:
        siglum = f" ({obj['siglum_s']})"

    return f"{obj['name_s']}{city}{siglum}"


def _format_person_label(obj: Dict) -> str:
    name: str = obj.get("name_s")
    dates: str = f" ({d})" if (d := obj.get("date_statement_s")) else ""

    return f"{name}{dates}"


def _format_incipit_label(obj: Dict) -> str:
    """
    The format for incipit titles is:

    Source title: Work num (supplied title)

    e.g., "Overtures - winds, stck: 1.1.1 (Allegro)"

    If the supplied title is not on the record, it will be omitted.

    :param obj: A Solr result object containing an incipit record
    :return: A string of the composite title
    """
    work_num: str = obj['work_num_s']
    source_title: str = obj["source_title_s"]
    title: str = f" ({d})" if (d := obj.get("title_s")) else ""

    return f"{source_title}: {work_num}{title}"

