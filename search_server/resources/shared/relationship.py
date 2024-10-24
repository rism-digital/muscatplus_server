import itertools
import logging
import re
from typing import Callable, Optional

import ypres

from shared_helpers.display_translators import (
    person_institution_relationship_labels_translator,
    place_relationship_labels_translator,
    qualifier_labels_translator,
    source_relationship_labels_translator,
    title_json_value_translator,
)
from shared_helpers.identifiers import (
    EXTERNAL_IDS,
    ID_SUB,
    PROJECT_ID_SUB,
    get_identifier,
)
from shared_helpers.utilities import to_aiter

log = logging.getLogger("mp_server")


class RelationshipsSection(ypres.AsyncDictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_section_label(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.relations", {})

    async def get_items(self, obj: dict) -> list[dict]:
        now_in: list = obj.get("now_in_json", [])
        contains: list = obj.get("contains_json", [])
        people: list = obj.get("related_people_json", [])
        institutions: list = obj.get("related_institutions_json", [])
        places: list = obj.get("related_places_json", [])
        sources: list = obj.get("related_sources_json", [])

        all_relationships = to_aiter(
            itertools.chain(now_in, contains, people, institutions, sources, places)
        )

        return await Relationship(
            all_relationships,
            many=True,
            context={
                "request": self.context.get("request"),
                "session": self.context.get("session"),
            },
        ).data


class Relationship(ypres.AsyncDictSerializer):
    role = ypres.MethodField()
    qualifier = ypres.MethodField()
    related_to = ypres.MethodField(label="relatedTo")
    name = ypres.MethodField()
    note = ypres.MethodField()

    def get_role(self, obj: dict) -> Optional[dict]:
        if "relationship" not in obj:
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
            rel = f"{relationship_value}"
        else:
            rel = f"relators:{relationship_value.replace(' ', '_')}"

        return {
            "label": relationship_translator(relationship_value, transl),
            "value": f"{rel}",
            "id": f"{rel}",
        }

    def get_qualifier(self, obj: dict) -> Optional[dict]:
        if "qualifier" not in obj:
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return {
            "label": qualifier_labels_translator(obj["qualifier"], transl),
            "value": f"{obj.get('qualifier')}",
            "id": f"rism:{obj.get('qualifier')}",
        }

    def get_related_to(self, obj: dict) -> Optional[dict]:
        req = self.context.get("request")
        if "person_id" in obj:
            return _related_to_person(req, obj)
        elif "institution_id" in obj:
            return _related_to_institution(req, obj)
        elif "place_id" in obj:
            return _related_to_place(req, obj)
        elif "source_id" in obj:
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
        if not {"person_id", "institution_id", "place_id"}.isdisjoint(obj.keys()):
            return None

        elif "name" in obj:
            # This will be selected as a non-linked label object
            # if we can't find an id to create a linkable object.
            return {"none": [obj["name"]]}
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
    if "date_statement" in obj:
        name = f"{obj.get('name')} ({obj.get('date_statement')})"
    else:
        name = f"{obj.get('name')}"

    person_id = re.sub(ID_SUB, "", obj["person_id"])

    return {
        "id": get_identifier(req, "people.person", person_id=person_id),
        "label": {"none": [name]},
        "type": "rism:Person",
    }


def _related_to_institution(req, obj: dict) -> dict:
    name: str = f"{obj['name']}"
    if "department" in obj:
        name = f"{name}, {obj.get('department')}"

    if "place" in obj:
        name = f"{name}, {obj['place']}"

    if "siglum" in obj:
        name = f"{name} ({obj.get('siglum')})"

    institution_id = re.sub(ID_SUB, "", obj["institution_id"])

    return {
        "id": get_identifier(
            req, "institutions.institution", institution_id=institution_id
        ),
        "label": {"none": [name]},
        "type": "rism:Institution",
    }


def _related_to_place(req, obj: dict) -> dict:
    place_id = re.sub(ID_SUB, "", obj["place_id"])

    return {
        "id": get_identifier(req, "places.place", place_id=place_id),
        "label": {"none": [obj.get("name")]},
        "type": "rism:Place",
    }


def _related_to_source(req, obj: dict) -> dict:
    transl: dict = req.ctx.translations

    source_id: str
    ident: str
    proj: Optional[str] = obj.get("project")

    if proj and proj in {"diamm", "cantus"}:
        source_id = re.sub(PROJECT_ID_SUB, "", obj["source_id"])
        prefix: Optional[str] = EXTERNAL_IDS.get(obj["project"], {}).get("ident")
        if not prefix:
            # If, for some reason this isn't found, return the empty dict.
            log.error("A URI prefix was not found for project %s", obj["project"])
            return {}
        spath = "source" if proj == "cantus" else "sources"
        suffix = f"{spath}/{source_id}"
        ident = prefix.format(ident=suffix)
    else:
        source_id = re.sub(ID_SUB, "", obj["source_id"])
        ident = get_identifier(req, "sources.source", source_id=source_id)

    source_title: dict = title_json_value_translator(obj.get("title", []), transl)

    return {"id": ident, "label": source_title, "type": "rism:Source"}


def _relationship_translator(obj: dict) -> Optional[Callable]:
    """
    We need different role translator functions for different types
    of relationships. This returns a function that is a suitable translator
    for a given value, depending on the keys that are available in the
    object.

    If we can't figure it out, return None and handle it in the caller.

    """
    if obj.get("project") == "diamm":
        # DIAMM uses the person / institution relator codes for its source relationships
        return person_institution_relationship_labels_translator
    elif "person_id" in obj or "institution_id" in obj:
        return person_institution_relationship_labels_translator
    elif "place_id" in obj:
        return place_relationship_labels_translator
    elif "source_id" in obj:
        return source_relationship_labels_translator
    elif "relationship" in obj:
        # To get around a bug where place IDs are not stored in Muscat, but the relationship
        # to them is. TODO: Fix this when the Muscat bug is fixed.
        return place_relationship_labels_translator
    else:
        return None
