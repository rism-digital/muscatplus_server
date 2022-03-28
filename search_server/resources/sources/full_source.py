import logging
import re
from typing import Optional

import serpy

from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.external_link import ExternalResourcesSection
from search_server.resources.sources.base_source import BaseSource
from search_server.resources.sources.contents import ContentsSection
from search_server.resources.sources.exemplars import ExemplarsSection
from search_server.resources.sources.incipits import IncipitsSection
from search_server.resources.sources.material_groups import MaterialGroupsSection
from search_server.resources.sources.references_notes import ReferencesNotesSection
from search_server.resources.shared.relationship import RelationshipsSection
from search_server.resources.sources.source_items import SourceItemsSection
from search_server.resources.sources.works import WorksSection

log = logging.getLogger(__name__)


class SourceItemList(JSONLDContextDictSerializer):
    sid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "sources.sourceitem_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.items_in_source")


class FullSource(BaseSource):
    contents = serpy.MethodField()
    material_groups = serpy.MethodField(
        label="materialGroups"
    )
    relationships = serpy.MethodField()
    incipits = serpy.MethodField()
    references_notes = serpy.MethodField(
        label="referencesNotes"
    )
    works = serpy.MethodField()
    exemplars = serpy.MethodField()
    items = serpy.MethodField()
    external_resources = serpy.MethodField(
        label="externalResources"
    )

    # In the full class view we don't want to display the summary as a top-level field
    # so we'll always return None.
    def get_summary(self, obj: dict) -> None:
        return None

    def get_contents(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        return ContentsSection(obj, context={"request": req}).data

    def get_material_groups(self, obj: SolrResult) -> Optional[dict]:
        if 'material_groups_json' not in obj:
            return None

        req = self.context.get("request")
        return MaterialGroupsSection(obj, context={"request": req}).data

    def get_relationships(self, obj: SolrResult) -> Optional[dict]:
        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return.
        if {'related_people_json', 'related_places_json', 'related_institutions_json', 'now_in_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")
        return RelationshipsSection(obj, context={"request": req}).data

    def get_incipits(self, obj: SolrResult) -> Optional[dict]:
        if not obj.get("has_incipits_b"):
            return None

        req = self.context.get("request")
        return IncipitsSection(obj, context={"request": req}).data

    def get_references_notes(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        refnotes: dict = ReferencesNotesSection(obj, context={"request": req}).data

        # if the only two keys in the references and notes section is 'label' and 'type'
        # then there is no content and we can hide this section.
        if {'notes', 'performanceLocations', 'liturgicalFestivals'}.isdisjoint(refnotes.keys()):
            return None

        return refnotes

    def get_works(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        wks: dict = WorksSection(obj, context={"request": req}).data
        if 'items' not in wks:
            return None

        return wks

    def get_exemplars(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        exmplrs: dict = ExemplarsSection(obj, context={"request": req}).data
        if 'items' not in exmplrs:
            return None

        return exmplrs

    def get_external_resources(self, obj: SolrResult) -> Optional[dict]:
        if 'external_resources_json' not in obj:
            return None

        return ExternalResourcesSection(obj, context={"request": self.context.get("request")}).data

    def get_items(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        itms: dict = SourceItemsSection(obj, context={"request": req}).data
        if 'items' not in itms:
            return None

        return itms
