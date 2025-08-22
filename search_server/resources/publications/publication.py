import re

import ypres

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.display_translators import work_catalogue_status_translator
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.record_history import get_record_history
from search_server.resources.shared.relationship import (
    Relationship,
    RelationshipsSection,
)


class Publication(ypres.AsyncDictSerializer):
    pid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="rism:Publication")
    type_label = ypres.MethodField(label="typeLabel")
    slabel = ypres.MethodField(label="label")
    creator = ypres.MethodField()
    composer = ypres.MethodField()
    summary = ypres.MethodField()
    relationships = ypres.MethodField()
    notes = ypres.MethodField()
    works = ypres.MethodField()
    record_history = ypres.MethodField(label="recordHistory")
    properties = ypres.MethodField()

    def get_pid(self, obj: dict) -> str:
        req = self.context["request"]
        pub_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(req, "publications.publication", publication_id=pub_id)

    def get_type_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        return transl["records.work_catalog"]

    def get_slabel(self, obj: dict) -> dict:
        return {"none": [obj["title_s"]]}

    def get_status(self, obj: dict) -> dict:
        req = self.context["request"]
        status = obj["work_catalogue_status_s"]
        transl: dict = req.ctx.translations
        labels = work_catalogue_status_translator(status, transl)
        return {"label": labels, "value": status}

    def get_creator(self, obj: dict) -> dict | None:
        if "creator_json" not in obj:
            return None

        return Relationship(
            obj["creator_json"][0],
            context={"request": self.context["request"]},
        ).serialized

    def get_composer(self, obj: dict) -> dict | None:
        if "composer_json" not in obj:
            return None

        jsobj = obj["composer_json"]
        req = self.context["request"]
        composer_id = re.sub(ID_SUB, "", jsobj["id"])
        composer_name: str = jsobj.get("name", "")
        composer_dates: str = jsobj.get("life_dates")

        name = f"{composer_name}{f' ({composer_dates})' if composer_dates else ''}"

        person_ident = get_identifier(req, "people.person", person_id=composer_id)

        return {"id": person_ident, "label": {"none": [name]}, "type": "rism:Person"}

    def get_summary(self, obj: dict) -> list[dict] | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            "short_title_s": ("records.short_title", None),
            "publication_place_sm": ("records.place_publication", None),
            "publisher_copyist_sm": ("records.publisher_copyist", None),
            "date_statements_sm": ("records.date", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_relationships(self, obj: dict) -> dict | None:
        if {"related_people_json", "related_institutions_json"}.isdisjoint(obj.keys()):
            return None

        return RelationshipsSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    def get_notes(self, obj: dict) -> dict | None:
        req = self.context["request"]
        notelist: dict = NotesSection(obj, context={"request": req}).serialized

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
                self.context["request"],
                "publications.publication_works",
                publication_id=publication_id,
            ),
            "totalItems": num_works,
        }

    def get_record_history(self, obj: dict) -> dict | None:
        if not self.context.get("direct_request", False):
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)

    def get_properties(self, obj: dict) -> dict | None:
        d = {}
        if abbrev := obj.get("short_title_s"):
            d["shortTitle"] = {"none": [abbrev]}
        if stmt := obj.get("date_statements_sm", []):
            d["publicationDates"] = {"none": ["; ".join(stmt)]}

        return {k: v for k, v in d.items() if v} or None
