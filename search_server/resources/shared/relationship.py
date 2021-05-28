import itertools
import re
from typing import Dict, Optional, List, Callable

import serpy as serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.display_translators import person_institution_relationship_labels_translator, \
    qualifier_labels_translator, place_relationship_labels_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer


class RelationshipsSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:RelationshipsSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.relations")

    def get_items(self, obj: Dict) -> List[Dict]:
        people: List = obj.get("related_people_json", [])
        institutions: List = obj.get("related_institutions_json", [])
        places: List = obj.get("related_places_json", [])

        all_relationships = itertools.chain(people, institutions, places)

        return Relationship(all_relationships,
                            many=True,
                            context={"request": self.context.get("request")}).data


class Relationship(JSONLDContextDictSerializer):
    stype = StaticField(
        label="type",
        value="rism:Relationship"
    )
    summary = serpy.MethodField()
    role = serpy.MethodField()
    qualifier = serpy.MethodField()
    related_to = serpy.MethodField(
        label="relatedTo"
    )

    def get_summary(self, obj: Dict) -> Optional[List]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        # We need different role translator functions for different types
        # of relationships.
        relationship_translator: Callable
        if 'person_id' in obj or 'institution_id' in obj:
            relationship_translator = person_institution_relationship_labels_translator
        elif 'place_id' in obj:
            relationship_translator = place_relationship_labels_translator
        elif 'relationship' in obj:
            # To get around a bug where place IDs are not stored in Muscat, but the relationship
            # to them is. TODO: Fix this when the Muscat bug is fixed.
            relationship_translator = place_relationship_labels_translator
        else:
            # We don't know what kind of data we're dealing with, so bail.
            return None

        field_config: LabelConfig = {
            "relationship": ("records.relation", relationship_translator),
            "qualifier": ("records.attribution_qualifier", qualifier_labels_translator),
        }
        return get_display_fields(obj, transl, field_config=field_config)

    def get_role(self, obj: Dict) -> Optional[str]:
        if 'relationship' not in obj:
            return None

        return f"rism:{obj.get('relationship').replace(' ', '_')}"

    def get_qualifier(self, obj: Dict) -> Optional[str]:
        if 'qualifier' not in obj:
            return None

        return f"rism:{obj.get('qualifier')}"

    def get_related_to(self, obj: Dict) -> Optional[Dict]:
        req = self.context.get("request")
        if 'person_id' in obj:
            return _related_to_person(req, obj)
        elif 'institution_id' in obj:
            return _related_to_institution(req, obj)
        elif 'place_id' in obj:
            return _related_to_place(req, obj)
        elif 'name' in obj:
            # This will be selected as a non-linked label object
            # if we can't find an id to create a linkable object.
            return {"none": [obj['name']]}
        else:
            # Something is wrong, but we can't find out what to display.
            return None


def _related_to_person(req, obj: Dict) -> Dict:
    name: str
    if 'date_statement' in obj:
        name = f"{obj.get('name')} ({obj.get('date_statement')})"
    else:
        name = f"{obj.get('name')}"

    person_id = re.sub(ID_SUB, "", obj.get('person_id'))

    return {
        "id": get_identifier(req, "people.person", person_id=person_id),
        "label": {"none": [name]},
        "type": "rism:Person"
    }


def _related_to_institution(req, obj: Dict) -> Dict:
    name: str
    if 'department' in obj:
        name = f"{obj.get('name')}, {obj.get('department')}"
    else:
        name = f"{obj.get('name')}"

    institution_id = re.sub(ID_SUB, "", obj.get("institution_id"))

    return {
        "id": get_identifier(req, "institutions.institution", institution_id=institution_id),
        "label": {"none": [name]},
        "type": "rism:Institution"
    }


def _related_to_place(req, obj: Dict) -> Dict:
    place_id = re.sub(ID_SUB, "", obj.get("place_id"))

    return {
        "id": get_identifier(req, "places.place", place_id=place_id),
        "label": {"none": [obj.get("name")]},
        "type": "rism:Place"
    }
