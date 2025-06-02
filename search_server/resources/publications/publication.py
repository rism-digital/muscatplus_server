import re

import ypres

from search_server.resources.shared.record_history import get_record_history
from shared_helpers.identifiers import ID_SUB, get_identifier


class Publication(ypres.AsyncDictSerializer):
    pid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="rism:Publication")
    type_label = ypres.MethodField(label="typeLabel")
    slabel = ypres.MethodField(label="label")
    record_history = ypres.MethodField(label="recordHistory")
    works = ypres.MethodField()

    def get_pid(self, obj: dict) -> str:
        req = self.context["request"]
        pub_id: str = re.sub(ID_SUB, "", obj["id"])

        return get_identifier(req, "publications.publication", publication_id=pub_id)

    def get_type_label(self, obj: dict) -> dict:
        # req = self.context["request"]
        # transl: dict = req.ctx.translations

        # TODO: Translations
        return {"none": ["Publication"]}

    def get_slabel(self, obj: dict) -> dict:
        return {"none": ["Title"]}

    def get_works(self, obj: dict) -> dict | None:
        if not self.context.get("direct_request"):
            return None

        num_works: int = obj.get("works_count_i", 0)
        if num_works == 0:
            return None

        publication_id: str = obj["rism_id"]

        return {
            "url": get_identifier(
                self.context["request"], "publications.publication_works", publication_id=publication_id
            ),
            "totalItems": num_works
        }

    def get_record_history(self, obj: dict) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)
