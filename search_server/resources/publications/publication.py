import re

import ypres

from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.record_history import get_record_history
from search_server.resources.shared.relationship import (
    Relationship,
    RelationshipsSection,
)
from shared_helpers.identifiers import ID_SUB, get_identifier


class Publication(ypres.AsyncDictSerializer):
    pid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="rism:Publication")
    type_label = ypres.MethodField(label="typeLabel")
    slabel = ypres.MethodField(label="label")
    creator = ypres.MethodField()
    relationships = ypres.MethodField()
    notes = ypres.MethodField()
    works = ypres.MethodField()
    record_history = ypres.MethodField(label="recordHistory")

    def get_pid(self, obj: dict) -> str:
        req = self.context["request"]
        pub_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(req, "publications.publication", publication_id=pub_id)

    def get_type_label(self, obj: dict) -> dict:
        # TODO: Translations
        return {"none": ["Publication"]}

    def get_slabel(self, obj: dict) -> dict:
        return {"none": [f"{obj["title_s"]}"]}

    def get_creator(self, obj: dict) -> dict | None:
        if "creator_json" not in obj:
            return None

        return Relationship(
            obj["creator_json"][0],
            context={
                "request": self.context["request"],
                "reltype": "rism:Creator"
            }).serialized

    def get_relationships(self, obj: dict) -> dict | None:
        if {"related_people_json",
            "related_institutions_json"
        }.isdisjoint(obj.keys()):
            return None

        return RelationshipsSection(
            obj,
            context={
                "request": self.context["request"]
            }).serialized

    def get_notes(self, obj: dict) -> dict | None:
        req = self.context["request"]
        notelist: dict = NotesSection(
            obj, context={"request": req}
        ).serialized

        # if the only two keys in the references and notes section is 'label' and 'type'
        # then there is no content and we can hide this section.
        if "notes" not in notelist:
            return None

        return notelist


    def get_works(self, obj: dict) -> dict | None:
        if not self.context.get("direct_request"):
            return None

        num_works: int = obj.get("works_count_i", 0)
        if num_works == 0:
            return None

        publication_id: str = obj["rism_id"]

        return {
            "sectionLabel": {"none": ["Works in this publication"]},
            "url": get_identifier(
                self.context["request"], "publications.publication_works", publication_id=publication_id
            ),
            "totalItems": num_works
        }

    def get_record_history(self, obj: dict) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)


