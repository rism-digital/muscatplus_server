import urllib.parse

import ypres
from small_asc.client import Results

from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.resources.incipits.incipit import (
    WorkIncipitsSection,
)
from search_server.resources.shared.external_authority import ExternalAuthoritiesSection
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.references_notes import ReferencesNotesSection
from search_server.resources.shared.relationship import RelationshipsSection
from search_server.resources.sources.base_source import (
    BaseSource,
)
from search_server.resources.works.base_work import BaseWork


class FullWork(BaseWork):
    incipits = ypres.MethodField()
    sources = ypres.MethodField()
    external_resources = ypres.MethodField(label="externalResources")
    external_authorities = ypres.MethodField(label="externalAuthorities")
    form_of_work = ypres.MethodField(label="formOfWork")
    references_notes = ypres.MethodField(label="referencesNotes")
    relationships = ypres.MethodField()
    properties = ypres.MethodField()
    dates = ypres.MethodField()

    async def get_incipits(self, obj: SolrResult) -> dict | None:
        if not obj.get("has_incipits_b", False):
            return None

        req = self.context["request"]
        return await WorkIncipitsSection(
            obj, context={"request": req, "direct_request": False}
        ).serialized

    def get_external_resources(self, obj: SolrResult) -> dict | None:
        if "external_resources_json" not in obj and not obj.get(
            "has_external_record_b", False
        ):
            return None

        return ExternalResourcesSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized

    def get_external_authorities(self, obj: SolrResult) -> dict | None:
        if "external_ids" not in obj:
            return None

        return ExternalAuthoritiesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    def get_sources(self, obj: SolrResult) -> dict | None:
        source_count: int = obj.get("source_count_i", 0)
        if source_count == 0:
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations
        work_id: str = obj["id"]
        ident: str = strip_prefix(work_id)

        d: dict = {
            "sectionLabel": transl.get("records.sources"),
            "url": get_identifier(req, "works.work_sources", work_id=ident),
            "totalItems": source_count,
        }

        return d

    def get_form_of_work(self, obj: SolrResult) -> dict | None:
        if "work_form_json" not in obj:
            return None

        return FormOfWorkSection(
            obj,
            context={"request": self.context["request"]},
        ).serialized

    def get_relationships(self, obj: SolrResult) -> dict | None:
        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return None.
        if {"related_people_json", "related_works_json"}.isdisjoint(obj.keys()):
            return None

        req = self.context["request"]
        return RelationshipsSection(obj, context={"request": req}).serialized

    def get_references_notes(self, obj: SolrResult) -> dict | None:
        req = self.context["request"]
        refnotes: dict = ReferencesNotesSection(
            obj, context={"request": req}
        ).serialized

        # if the only two keys in the references and notes section is 'label' and 'type'
        # then there is no content and we can hide this section.
        if {"notes", "performanceLocations", "liturgicalFestivals"}.isdisjoint(
            refnotes.keys()
        ):
            return None

        return refnotes

    def get_dates(self, obj: SolrResult) -> dict | None:
        if "date_ranges_im" not in obj:
            return None

        earliest, latest = obj.get("date_ranges_im", [None, None])

        d: dict = {
            "earliestDate": earliest,
            "latestDate": latest,
            "dateStatement": obj.get("date_statement_s", []),
        }

        return {k: v for k, v in d.items() if v}

    def get_properties(self, obj: SolrResult) -> dict | None:
        d: dict = {
            "keyMode": obj.get("key_mode_s"),
        }

        return {k: v for k, v in d.items() if v} or None


class FormOfWorkSection(ypres.DictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl.get("records.form_of_work", {})

    def get_items(self, obj) -> list:
        return FormOfWork(
            obj["work_form_json"],
            many=True,
            context={"request": self.context["request"]},
        ).serialized_many


class FormOfWork(ypres.DictSerializer):
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


async def get_source_objects(req, work_id: str) -> list | None:
    fq = ["type:source", f"work_ids:{work_id}"]

    sort: str = "main_title_ans asc"
    source_results: Results = await SolrConnection.search(
        {
            "query": "*:*",
            "filter": fq,
            "sort": sort,
        },
        cursor=True,
    )

    if source_results.hits == 0:
        return None

    items: list[dict] = []

    async for res in source_results:
        items.append(await BaseSource(res, context={"request": req}).serialized)

    return items or None
