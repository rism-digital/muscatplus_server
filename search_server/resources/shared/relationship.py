import itertools
import re
from collections.abc import Callable

import ypres
from sanic.log import logger

from search_server.helpers.display_translators import (
    person_institution_relationship_labels_translator,
    place_relationship_labels_translator,
    qualifier_labels_translator,
    source_relationship_labels_translator,
    title_json_value_translator,
    work_relationship_labels_translator,
)
from search_server.helpers.identifiers import (
    EXTERNAL_IDS,
    LOC_RELATOR_BASE,
    RDAU_BASE,
    RISM_RELATIONSHIP_BASE,
    get_identifier,
    strip_prefix,
)

_LOC_RELATOR_CODE_RE = re.compile(r"^[a-z]{3}$")


class RelationshipsSection(ypres.DictSerializer):
    sid = ypres.MethodField(label="id")
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_sid(self, obj: dict) -> str | None:
        req = self.context["request"]
        route_name = self.context["section_route"]
        route_params = self.context["route_params"]

        return get_identifier(req, route_name, **route_params)

    def get_section_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl.get("records.relations", {})

    def get_items(self, obj: dict) -> list[dict]:
        now_in: list = obj.get("now_in_json", [])
        contains: list = obj.get("contains_json", [])
        people: list = obj.get("related_people_json", [])
        institutions: list = obj.get("related_institutions_json", [])
        places: list = obj.get("related_places_json", [])
        sources: list = obj.get("related_sources_json", [])
        works: list = obj.get("related_works_json", [])
        contributing_projects: list = obj.get("contributing_projects_json", [])

        all_relationships = itertools.chain(
            now_in,
            contains,
            people,
            institutions,
            sources,
            works,
            places,
            contributing_projects,
        )

        return Relationship(
            all_relationships,
            many=True,
            context={
                "request": self.context["request"],
            },
        ).serialized_many


class Relationship(ypres.DictSerializer):
    role = ypres.MethodField()
    qualifier = ypres.MethodField()
    related_to = ypres.MethodField(label="relatedTo")
    name = ypres.MethodField()
    note = ypres.MethodField()
    project_url = ypres.MethodField()

    def get_role(self, obj: dict) -> dict | None:
        if "relationship" not in obj:
            return None

        relationship_value: str = obj["relationship"]
        req = self.context["request"]
        transl: dict = req.ctx.translations
        relationship_translator: Callable | None = _relationship_translator(obj)
        if not relationship_translator:
            return {"none": ["[Unknown relationship]"]}

        canonical_id: str = _canonical_role_id(relationship_value)

        return {
            "id": canonical_id,
            "label": relationship_translator(relationship_value, transl),
            "value": relationship_value,
        }

    def get_qualifier(self, obj: dict) -> dict | None:
        if "qualifier" not in obj:
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return {
            "label": qualifier_labels_translator(obj["qualifier"], transl),
            "value": f"{obj.get('qualifier')}",
            "id": f"rism:{obj.get('qualifier')}",
        }

    def get_related_to(self, obj: dict) -> dict | None:
        req = self.context["request"]

        if "person_id" in obj:
            return _related_to_person(req, obj)
        elif "institution_id" in obj:
            return _related_to_institution(req, obj)
        elif "place_id" in obj:
            return _related_to_place(req, obj)
        elif "source_id" in obj:
            return _related_to_source(req, obj)
        elif "work_id" in obj:
            return _related_to_work(req, obj)
        else:
            # Something is wrong, but we can't find out what to display.
            return None

    def get_name(self, obj: dict) -> dict | None:
        # This is displayed if all we have for the related-to is a string, not a linked
        # object.
        # if any of these keys are in the object, then we have a relationship and it should be handled
        # by the 'related_to' function. This is done by seeing if the set of expected keys, and the set
        # of actual keys, have any overlap. If they do, bail.
        if not {"person_id", "institution_id", "place_id", "work_id"}.isdisjoint(
            obj.keys()
        ):
            return None

        elif "name" in obj:
            # This will be selected as a non-linked label object
            # if we can't find an id to create a linkable object.
            return {"none": [obj["name"]]}

        # we have neither a related object, nor a name, so how could any reasonable person expect us
        # to do anything with this? Just bail, and hope someone fixes the data.
        return None

    def get_note(self, obj: dict) -> dict | None:
        if "note" not in obj:
            return None

        return {"none": [obj.get("note")]}

    def get_project_url(self, obj: dict) -> dict | None:
        # For contributing projects a Project URL is given.
        if "project_url" not in obj:
            return None

        return obj.get("project_url")


def _related_to_person(req, obj: dict) -> dict:
    name: str
    if "date_statement" in obj:
        name = f"{obj.get('name')} ({obj.get('date_statement')})"
    else:
        name = f"{obj.get('name')}"

    person_id = strip_prefix(obj["person_id"])

    return {
        "id": get_identifier(req, "people.person", person_id=person_id),
        "label": {"none": [name]},
        "type": "rism:Person",
    }


def _related_to_institution(req, obj: dict) -> dict:
    name: str = f"{obj['name']}"

    if "place" in obj:
        name = f"{name}, {obj['place']}"

    if "siglum" in obj:
        name = f"{name} ({obj.get('siglum')})"

    institution_id = strip_prefix(obj["institution_id"])

    return {
        "id": get_identifier(
            req, "institutions.institution", institution_id=institution_id
        ),
        "label": {"none": [name]},
        "type": "rism:Institution",
    }


def _related_to_place(req, obj: dict) -> dict:
    place_id = strip_prefix(obj["place_id"])
    name = [obj["name"]]

    if "district" in obj:
        name.append(obj["district"])

    if "country" in obj:
        name.append(obj["country"])

    full_name: str = ", ".join(name)

    return {
        "id": get_identifier(req, "places.place", place_id=place_id),
        "label": {"none": [full_name]},
        "type": "rism:Place",
    }


def _related_to_source(req, obj: dict) -> dict:
    transl: dict = req.ctx.translations

    source_id: str
    ident: str
    proj: str | None = obj.get("project")

    if proj and proj in {"diamm", "cantus"}:
        source_id = strip_prefix(obj["source_id"])
        prefix: str | None = EXTERNAL_IDS.get(obj["project"], {}).get("ident")
        if not prefix:
            # If, for some reason this isn't found, return the empty dict.
            logger.error("A URI prefix was not found for project %s", obj["project"])
            return {}
        spath = "source" if proj == "cantus" else "sources"
        suffix = f"{spath}/{source_id}"
        ident = prefix.format(ident=suffix)
    else:
        source_id = strip_prefix(obj["source_id"])
        ident = get_identifier(req, "sources.source", source_id=source_id)

    source_title: dict = title_json_value_translator(obj.get("title", []), transl)

    return {"id": ident, "label": source_title, "type": "rism:Source"}


def _related_to_work(req, obj: dict) -> dict:
    work_id: str = strip_prefix(obj["work_id"])
    ident: str = get_identifier(req, "works.work", work_id=work_id)
    work_title: dict = {"none": [obj.get("title", "[No title]")]}

    return {"id": ident, "label": work_title, "type": "rism:Work"}


def _relationship_translator(obj: dict) -> Callable | None:
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
    elif "work_id" in obj:
        return work_relationship_labels_translator
    elif "relationship" in obj:
        # To get around a bug where place IDs are not stored in Muscat, but the relationship
        # to them is. TODO: Fix this when the Muscat bug is fixed.
        return place_relationship_labels_translator
    else:
        return None


def _canonical_role_id(relationship_value: str) -> str:
    """Canonical URI for relationship roles in JSON-LD output."""
    if relationship_value.startswith("http://") or relationship_value.startswith(
        "https://"
    ):
        return relationship_value

    if relationship_value.startswith("rdau:"):
        return relationship_value.replace("rdau:", RDAU_BASE, 1)

    relator_code = relationship_value
    if relationship_value.startswith("relators:"):
        relator_code = relationship_value.split(":", 1)[1]

    # MARC relator codes remain in LoC namespace.
    if _LOC_RELATOR_CODE_RE.match(relator_code):
        return f"{LOC_RELATOR_BASE}{relator_code}"

    slug_source = (
        relator_code
        if relationship_value.startswith("relators:")
        else relationship_value
    )
    slug = (
        slug_source.strip()
        .lower()
        .replace(":", "_")
        .replace(" ", "_")
        .replace("-", "_")
    )
    return f"{RISM_RELATIONSHIP_BASE}{slug}"
