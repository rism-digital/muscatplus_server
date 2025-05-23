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
        pass

    def get_record_history(self, obj: dict) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_record_history(obj, transl)
