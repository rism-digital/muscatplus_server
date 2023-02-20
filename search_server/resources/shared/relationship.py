import itertools
import logging
import re
from typing import Optional, Callable

import serpy

from shared_helpers.display_translators import (
    person_institution_relationship_labels_translator,
    qualifier_labels_translator,
    place_relationship_labels_translator, title_json_value_translator, source_relationship_labels_translator
)
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult

log = logging.getLogger(__name__)


class RelationshipsSection(serpy.DictSerializer):
    rid = serpy.MethodField(
        label="id"
    )
    rtype = serpy.StaticField(
        label="type",
        value="rism:RelationshipsSection"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_rid(self, obj: SolrResult) -> str:
        req = self.context.get('request')
        related_id_val = obj["id"]
        related_id_type = obj["type"]
        relationship_id: str = re.sub(ID_SUB, "", related_id_val)

        uri_section: str = ""
        kwargs: dict = {}

        if related_id_type == "source":
            uri_section = "sources.relationships"
            kwargs = {"source_id": relationship_id}
        elif related_id_type == "person":
            uri_section = "people.relationships"
            kwargs = {"person_id": relationship_id}
        elif related_id_type == "institution":
            uri_section = "institutions.relationships"
            kwargs = {"institution_id": relationship_id}
        elif related_id_type == "holding":
            uri_section = "holdings.relationships"
            holding_id_val: str = obj["holding_id_sni"]
            if "-" in holding_id_val:
                holding_id, source_id = holding_id_val.split("-")
            else:
                holding_id = relationship_id
                source_id = relationship_id

            kwargs = {"source_id": source_id, "holding_id": holding_id}
        elif related_id_type == "material-group":
            uri_section = "sources.material_group_relationships"
            source_id = re.sub(ID_SUB, "", obj["source_id"])
            kwargs = {"source_id": source_id, "mg_id": relationship_id}

        return get_identifier(req, uri_section, **kwargs)

    def get_label(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.relations", {})

    def get_items(self, obj: dict) -> list[dict]:
        people: list = obj.get("related_people_json", [])
        institutions: list = obj.get("related_institutions_json", [])
        places: list = obj.get("related_places_json", [])
        now_in: list = obj.get("now_in_json", [])
        sources: list = obj.get("related_sources_json", [])

        all_relationships = itertools.chain(people, institutions, places, now_in, sources)

        return Relationship(all_relationships,
                            many=True,
                            context={"request": self.context.get("request")}).data


class Relationship(serpy.DictSerializer):
    sid = serpy.MethodField(
        label="id"
    )
    stype = serpy.MethodField(
        label="type"
    )
    role = serpy.MethodField()
    qualifier = serpy.MethodField()
    related_to = serpy.MethodField(
        label="relatedTo"
    )
    name = serpy.MethodField()
    note = serpy.MethodField()

    def get_sid(self, obj: dict) -> str:
        ctx: dict = self.context
        req = ctx.get("request")
        source_id: str = re.sub(ID_SUB, "", obj["this_id"])
        if "reltype" in ctx and ctx["reltype"] == "rism:Creator":
            return get_identifier(req, "sources.creator", source_id=source_id)

        relationship_id: str = obj["id"]
        return get_identifier(req, "sources.relationship", source_id=source_id, relationship_id=relationship_id)

    def get_stype(self, obj: dict) -> str:
        ctx: dict = self.context
        if "reltype" in ctx:
            return ctx["reltype"]

        return "rism:Relationship"

    def get_role(self, obj: dict) -> Optional[dict]:
        if 'relationship' not in obj:
            return None

        relationship_value: str = obj["relationship"]
        req = self.context.get("request")
        transl: dict = req.ctx.translations
        relationship_translator: Optional[Callable] = _relationship_translator(obj)
        if not relationship_translator:
            return {"none": ["[Unknown relationship]"]}

        # If the relator codes are already formatted as a namespace, then don't double
        # namespace them.
        if relationship_value.startswith("rdau"):
            rel = relationship_value
        else:
            rel = relationship_value.replace(' ', '_')

        return {
            "label": relationship_translator(relationship_value, transl),
            "value": f"{rel}",
            "type": f"relators:{rel}"
        }

    def get_qualifier(self, obj: dict) -> Optional[dict]:
        if 'qualifier' not in obj:
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return {
            "label": qualifier_labels_translator(obj['qualifier'], transl),
            "value": f"{obj.get('qualifier')}",
            "type": f"rism:{obj.get('qualifier')}"
        }

    def get_related_to(self, obj: dict) -> Optional[dict]:
        req = self.context.get("request")
        if 'person_id' in obj:
            return _related_to_person(req, obj)
        elif 'institution_id' in obj:
            return _related_to_institution(req, obj)
        elif 'place_id' in obj:
            return _related_to_place(req, obj)
        elif 'source_id' in obj:
            return _related_to_source(req, obj)
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

    def get_note(self, obj: dict) -> Optional[dict]:
        if "note" not in obj:
            return None

        return {"none": [obj.get("note")]}


def _related_to_person(req, obj: dict) -> dict:
    name: str
    if 'date_statement' in obj:
        name = f"{obj.get('name')} ({obj.get('date_statement')})"
    else:
        name = f"{obj.get('name')}"

    person_id = re.sub(ID_SUB, "", obj['person_id'])

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

    institution_id = re.sub(ID_SUB, "", obj["institution_id"])

    return {
        "id": get_identifier(req, "institutions.institution", institution_id=institution_id),
        "label": {"none": [name]},
        "type": "rism:Institution"
    }


def _related_to_place(req, obj: dict) -> dict:
    place_id = re.sub(ID_SUB, "", obj["place_id"])

    return {
        "id": get_identifier(req, "places.place", place_id=place_id),
        "label": {"none": [obj.get("name")]},
        "type": "rism:Place"
    }


def _related_to_source(req, obj: dict) -> dict:
    transl: dict = req.ctx.translations

    source_id: str = re.sub(ID_SUB, "", obj["source_id"])
    source_title: dict = title_json_value_translator(obj.get("title", []), transl)

    return {
        "id": get_identifier(req, "sources.source", source_id=source_id),
        "label": source_title,
        "type": "rism:Source"
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
    elif 'source_id' in obj:
        return source_relationship_labels_translator
    elif 'relationship' in obj:
        # To get around a bug where place IDs are not stored in Muscat, but the relationship
        # to them is. TODO: Fix this when the Muscat bug is fixed.
        return place_relationship_labels_translator
    else:
        return None
