import logging
import re
from typing import Optional

import serpy

from search_server.resources.incipits.incipit import IncipitsSection
from search_server.resources.shared.digital_objects import DigitalObjectsSection
from search_server.resources.shared.external_link import ExternalResourcesSection
from search_server.resources.shared.relationship import RelationshipsSection
from search_server.resources.sources.base_source import BaseSource
from search_server.resources.sources.contents import ContentsSection
from search_server.resources.sources.exemplars import ExemplarsSection
from search_server.resources.sources.material_groups import MaterialGroupsSection
from search_server.resources.sources.references_notes import ReferencesNotesSection
from search_server.resources.sources.source_items import SourceItemsSection
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult

log = logging.getLogger("mp_server")


class SourceItemList(serpy.DictSerializer):
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
        transl: dict = req.ctx.translations

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
    exemplars = serpy.MethodField()
    source_items = serpy.MethodField(
        label="sourceItems"
    )
    external_resources = serpy.MethodField(
        label="externalResources"
    )
    digital_objects = serpy.MethodField(
        label="digitalObjects"
    )
    dates = serpy.MethodField()
    properties = serpy.MethodField()

    # In the full class view we don't want to display the summary as a top-level field
    # so we'll always return None.
    def get_summary(self, obj: dict) -> None:
        return None

    def get_contents(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        return ContentsSection(obj, context={"request": req,
                                             "session": self.context.get("session")}).data

    def get_material_groups(self, obj: SolrResult) -> Optional[dict]:
        if 'material_groups_json' not in obj:
            return None

        req = self.context.get("request")
        return MaterialGroupsSection(obj, context={"request": req,
                                                   "session": self.context.get("session")}).data

    def get_relationships(self, obj: SolrResult) -> Optional[dict]:
        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return.
        if {'related_people_json', 'related_places_json', 'related_institutions_json', 'now_in_json', 'related_sources_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")
        return RelationshipsSection(obj, context={"request": req,
                                                  "session": self.context.get("session")}).data

    async def get_incipits(self, obj: SolrResult) -> Optional[dict]:
        if not obj.get("has_incipits_b", False):
            return None

        req = self.context.get("request")
        return await IncipitsSection(obj, context={"request": req,
                                                   "session": self.context.get("session")}).data

    def get_references_notes(self, obj: SolrResult) -> Optional[dict]:
        req = self.context.get("request")
        refnotes: dict = ReferencesNotesSection(obj, context={"request": req,
                                                              "session": self.context.get("session")}).data

        # if the only two keys in the references and notes section is 'label' and 'type'
        # then there is no content and we can hide this section.
        if {'notes', 'performanceLocations', 'liturgicalFestivals'}.isdisjoint(refnotes.keys()):
            return None

        return refnotes

    async def get_exemplars(self, obj: SolrResult) -> Optional[dict]:
        # If this record does not have any physical copies attached to it ("Holdings", either
        # print holdings or a manuscript holding record) then bypass the solr query that will retrieve
        # zero records.
        if "num_physical_copies_i" not in obj:
            return None

        return await ExemplarsSection(obj, context={"request": self.context.get("request"),
                                                    "session": self.context.get("session")}).data

    def get_external_resources(self, obj: SolrResult) -> Optional[dict]:
        if 'external_resources_json' not in obj:
            return None

        return ExternalResourcesSection(obj, context={"request": self.context.get("request"),
                                                      "session": self.context.get("session")}).data

    async def get_source_items(self, obj: SolrResult) -> Optional[dict]:
        if "num_source_members_i" not in obj:
            return None

        return await SourceItemsSection(obj, context={"request": self.context.get("request"),
                                                      "session": self.context.get("session")}).data

    async def get_digital_objects(self, obj: SolrResult) -> Optional[dict]:
        if not obj.get("has_digital_objects_b", False):
            return None

        return await DigitalObjectsSection(obj, context={"request": self.context.get("request"),
                                                         "session": self.context.get("session")}).data

    def get_dates(self, obj: SolrResult) -> Optional[dict]:
        if "date_ranges_im" not in obj:
            return None

        earliest, latest = obj.get("date_ranges_im", [None, None])

        d: dict = {
            "earliestDate": earliest,
            "latestDate": latest,
            "dateStatement": ", ".join(obj.get("date_statements_sm", []))
        }

        return {k: v for k, v in d.items() if v}

    def get_properties(self, obj: SolrResult) -> Optional[dict]:
        d: dict = {
            "keyMode": obj.get("key_mode_s")
        }

        return {k: v for k, v in d.items() if v} or None
