import ypres

from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.incipits.incipit import IncipitsSection
from search_server.resources.shared.digital_objects import DigitalObjectsSection
from search_server.resources.shared.external_resources import ExternalResourcesSection
from search_server.resources.shared.references_notes import ReferencesNotesSection
from search_server.resources.shared.relationship import RelationshipsSection
from search_server.resources.sources.base_source import BaseSource
from search_server.resources.sources.contents import ContentsSection
from search_server.resources.sources.exemplars import ExemplarsSection
from search_server.resources.sources.material_groups import MaterialGroupsSection
from search_server.resources.sources.source_items import SourceItemsSection
from search_server.resources.sources.works import WorksSection


class SourceItemList(ypres.DictSerializer):
    sid = ypres.MethodField(label="id")
    silabel = ypres.MethodField(label="label")

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        source_id: str = strip_prefix(obj["source_id"])

        return get_identifier(req, "sources.sourceitem_list", source_id=source_id)

    def get_silabel(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.items_in_source"]


class FullSource(BaseSource):
    contents = ypres.MethodField()
    material_groups = ypres.MethodField(label="materialGroups")
    relationships = ypres.MethodField()
    incipits = ypres.MethodField()
    references_notes = ypres.MethodField(label="referencesNotes")
    exemplars = ypres.MethodField()
    source_items = ypres.MethodField(label="sourceItems")
    external_resources = ypres.MethodField(label="externalResources")
    digital_objects = ypres.MethodField(label="digitalObjects")
    dates = ypres.MethodField()
    works = ypres.MethodField()
    properties = ypres.MethodField()

    # In the full class view we don't want to display the summary as a top-level field
    # so we'll always return None.
    def get_summary(self, obj: dict) -> None:
        return None

    def get_contents(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        return ContentsSection(  # type: ignore
            obj, context={"request": req}
        ).serialized

    def get_material_groups(self, obj: SolrResult) -> dict | None:
        if "material_groups_json" not in obj:
            return None

        req = self.context["request"]
        return MaterialGroupsSection(obj, context={"request": req}).serialized

    def get_relationships(self, obj: SolrResult) -> dict | None:
        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return.
        if {
            "related_people_json",
            "related_places_json",
            "related_institutions_json",
            "now_in_json",
            "related_sources_json",
        }.isdisjoint(obj.keys()):
            return None

        req = self.context["request"]
        return RelationshipsSection(obj, context={"request": req}).serialized

    async def get_incipits(self, obj: SolrResult) -> dict | None:
        if not obj.get("has_incipits_b", False):
            return None

        req = self.context["request"]
        return await IncipitsSection(obj, context={"request": req}).serialized

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

    async def get_exemplars(self, obj: SolrResult) -> dict | None:
        # If this record does not have any physical copies attached to it ("Holdings", either
        # print holdings or a manuscript holding record) then bypass the solr query that will retrieve
        # zero records.
        if "num_physical_copies_i" not in obj:
            return None

        return await ExemplarsSection(
            obj,
            context={
                "request": self.context["request"],
            },
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

    async def get_source_items(self, obj: SolrResult) -> dict | None:
        if "num_source_members_i" not in obj:
            return None

        return await SourceItemsSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized

    async def get_digital_objects(self, obj: SolrResult) -> dict | None:
        if not obj.get("has_digital_objects_b", False):
            return None

        return await DigitalObjectsSection(
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized

    def get_works(self, obj: SolrResult) -> dict | None:
        if {"work_node_json", "works_json"}.isdisjoint(obj.keys()):
            return None

        return WorksSection(  # type: ignore
            obj,
            context={
                "request": self.context["request"],
            },
        ).serialized

    def get_dates(self, obj: SolrResult) -> dict | None:
        if "date_ranges_im" not in obj:
            return None

        earliest, latest = obj.get("date_ranges_im", [None, None])

        d: dict = {
            "earliestDate": earliest,
            "latestDate": latest,
            "dateStatement": ", ".join(obj.get("date_statements_sm", [])),
        }

        return {k: v for k, v in d.items() if v}

    def get_properties(self, obj: SolrResult) -> dict | None:
        d: dict = {
            "keyMode": obj.get("key_mode_s"),
            "physicalDimensions": obj.get("physical_dimensions_sm"),
        }

        return {k: v for k, v in d.items() if v} or None
