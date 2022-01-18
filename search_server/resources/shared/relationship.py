import itertools
import logging
import re
from typing import Optional, Callable

import serpy

from search_server.helpers.display_translators import person_institution_relationship_labels_translator, \
    qualifier_labels_translator, place_relationship_labels_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer

log = logging.getLogger(__name__)


class RelationshipsSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:RelationshipsSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.relations")

    def get_items(self, obj: dict) -> list[dict]:
        people: list = obj.get("related_people_json", [])
        institutions: list = obj.get("related_institutions_json", [])
        places: list = obj.get("related_places_json", [])

        all_relationships = itertools.chain(people, institutions, places)

        return Relationship(all_relationships,
                            many=True,
                            context={"request": self.context.get("request")}).data


class Relationship(JSONLDContextDictSerializer):
    stype = StaticField(
        label="type",
        value="rism:Relationship"
    )
    label = serpy.MethodField()
    role = serpy.MethodField()
    qualifier = serpy.MethodField()
    qualifier_label = serpy.MethodField(
        label="qualifierLabel"
    )
    related_to = serpy.MethodField(
        label="relatedTo"
    )
    name = serpy.MethodField()

    def get_label(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations
        relationship_translator: Optional[Callable] = _relationship_translator(obj)
        if not relationship_translator:
            return {"none": ["[Unknown relationship]"]}

        return relationship_translator(obj.get("relationship"), transl)

    def get_role(self, obj: dict) -> Optional[str]:
        if 'relationship' not in obj:
            return None

        return f"rism:{obj.get('relationship').replace(' ', '_')}"

    def get_qualifier(self, obj: dict) -> Optional[str]:
        if 'qualifier' not in obj:
            return None

        return f"rism:{obj.get('qualifier')}"

    def get_qualifier_label(self, obj: dict) -> Optional[dict]:
        if 'qualifier' not in obj:
            return None

        req = self.context.get("request")
        transl = req.app.ctx.translations

        return qualifier_labels_translator(obj['qualifier'], transl)

    def get_related_to(self, obj: dict) -> Optional[dict]:
        req = self.context.get("request")
        if 'person_id' in obj:
            return _related_to_person(req, obj)
        elif 'institution_id' in obj:
            return _related_to_institution(req, obj)
        elif 'place_id' in obj:
            return _related_to_place(req, obj)
        else:
            # Something is wrong, but we can't find out what to display.
            return None

    def get_name(self, obj: dict) -> Optional[dict]:
        # This is displayed if all we have for the related-to is a string, not a linked
        # object.
        # if any of these keys are in the object, then we have a relationship and it should be handled
        # by the 'related_to' function. This is done by seeing if the set of expected keys, and the set
        # of actual keys, have any overlap. If they do, bail.
        if not {'person_id', 'institution_id', 'place_id'}.isdisjoint(obj.keys()):
            return None

        elif 'name' in obj:
            # This will be selected as a non-linked label object
            # if we can't find an id to create a linkable object.
            return {"none": [obj['name']]}
        else:
            # we have neither a related object, nor a name, so how could any reasonable person expect us
            # to do anything with this? Just bail, and hope someone fixes the data.
            return None


def _related_to_person(req, obj: dict) -> dict:
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


def _related_to_institution(req, obj: dict) -> dict:
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


def _related_to_place(req, obj: dict) -> dict:
    place_id = re.sub(ID_SUB, "", obj.get("place_id"))

    return {
        "id": get_identifier(req, "places.place", place_id=place_id),
        "label": {"none": [obj.get("name")]},
        "type": "rism:Place"
    }


def _relationship_translator(obj: dict) -> Optional[Callable]:
    """
    We need different role translator functions for different types
    of relationships. This returns a function that is a suitable translator
    for a given value, depending on the keys that are available in the
    object.

    If we can't figure it out, return None and handle it in the caller.

    """
    relationship_translator: Callable
    if 'person_id' in obj or 'institution_id' in obj:
        return person_institution_relationship_labels_translator
    elif 'place_id' in obj:
        return place_relationship_labels_translator
    elif 'relationship' in obj:
        # To get around a bug where place IDs are not stored in Muscat, but the relationship
        # to them is. TODO: Fix this when the Muscat bug is fixed.
        return place_relationship_labels_translator
    else:
        return None
