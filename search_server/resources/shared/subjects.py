import urllib.parse

import ypres

from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.solr_connection import SolrResult


class SubjectsSection(ypres.DictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.subject_headings"]

    def get_items(self, obj: SolrResult) -> list:
        return Subject(
            obj["subjects_json"],
            many=True,
            context={
                "request": self.context["request"],
            },
        ).serialized_many


# A minimal subject serializer. This is because the data for the subjects
# comes from the JSON field on the source, rather than from the Solr records
# for subjects.
class Subject(ypres.DictSerializer):
    sid = ypres.MethodField(label="id")
    stype = ypres.StaticField(label="type", value="rism:Subject")
    slabel = ypres.MethodField(label="label")
    value = ypres.MethodField()

    def get_sid(self, obj: dict) -> str:
        req = self.context["request"]
        subject_id: str = strip_prefix(obj["id"])

        return get_identifier(req, "subjects.subject", subject_id=subject_id)

    def get_slabel(self, obj: dict) -> dict:
        return {"none": [obj.get("subject")]}

    def get_value(self, obj: dict) -> str:
        if "subject" not in obj:
            return ""
        return urllib.parse.quote_plus(obj["subject"])
