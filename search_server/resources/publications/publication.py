import ypres

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.identifiers import get_identifier
from search_server.resources.publications.base_publication import BasePublication
from search_server.resources.shared.notes import NotesSection
from search_server.resources.shared.relationship import (
    RelationshipsSection,
)


class Publication(BasePublication):
    summary = ypres.MethodField()
    relationships = ypres.MethodField()
    notes = ypres.MethodField()
    works = ypres.MethodField()

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
