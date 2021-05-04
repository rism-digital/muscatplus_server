import logging
import re
from typing import Dict, List, Optional

import pysolr
import serpy

from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.resources.shared.relationship import Relationship
from search_server.resources.sources.base_source import BaseSource
from search_server.resources.sources.contents import ContentsSection
from search_server.resources.sources.exemplars import ExemplarsSection
from search_server.resources.sources.incipits import IncipitsSection
from search_server.resources.sources.material_groups import MaterialGroupsSection
from search_server.resources.sources.relationships import RelationshipsSection
from search_server.resources.sources.references_notes import ReferencesNotesSection
from search_server.resources.sources.source_items import SourceItemsSection
from search_server.resources.sources.works import WorksSection

log = logging.getLogger(__name__)


def _source_lookup(source_id: str) -> Optional[Dict]:
    """ Helper method for looking up a single source. """
    fq: List = ["type:source",
                f"id:source_{source_id}"]

    # TODO: Fill in the `fl` parameter to only retrieve the fields that are necessary for representing the source.
    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    return record.docs[0]


def handle_source_request(req, source_id: str) -> Optional[Dict]:
    source_record: Optional[Dict] = _source_lookup(source_id)
    if not source_record:
        return None

    return FullSource(source_record, context={"request": req,
                                              "direct_request": True}).data


def handle_people_relationships_list_request(req, source_id: str) -> Optional[Dict]:
    # TODO: Do we want to create a search interface? Or is just listing them enough? What happens
    #   if we have hundreds of relationships?
    pass


def handle_person_relationship_request(req, source_id: str, relationship_id: str) -> Optional[Dict]:
    source_record: Optional[Dict] = _source_lookup(source_id)
    if not source_record:
        return None

    if 'related_people_json' not in source_record:
        return None

    target_relationship: List = [f for f in source_record['related_people_json'] if f.get("id") == relationship_id]
    if not target_relationship:
        return None

    return Relationship(target_relationship[0], context={"request": req,
                                                               "direct_request": True}).data


def handle_institutions_relationships_list_request(req, source_id: str) -> Optional[Dict]:
    pass


def handle_institution_relationship_request(req, source_id: str, relationship_id: str) -> Optional[Dict]:
    source_record: Optional[Dict] = _source_lookup(source_id)
    if not source_record:
        return None

    if 'related_institutions_json' not in source_record:
        return None

    target_relationship: List = [f for f in source_record["related_institutions_json"] if f.get("id") == relationship_id]
    if not target_relationship:
        return None

    return Relationship(target_relationship[0], context={"request": req,
                                                                    "direct_request": True}).data


def handle_creator_request(req, source_id: str) -> Optional[Dict]:
    source_record: Optional[Dict] = _source_lookup(source_id)
    if not source_record:
        return None

    if 'creator_json' not in source_record:
        return None

    creator = source_record['creator_json'][0]

    return Relationship(creator, context={"request": req,
                                                "direct_request": True}).data


class SourceItemList(JSONLDContextDictSerializer):
    sid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()

    def get_sid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "sources.sourceitem_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

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

    def get_contents(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        return ContentsSection(obj, context={"request": req}).data

    def get_material_groups(self, obj: SolrResult) -> Optional[Dict]:
        if 'material_groups_json' not in obj:
            return None

        req = self.context.get("request")
        return MaterialGroupsSection(obj, context={"request": req}).data

    def get_relationships(self, obj: SolrResult) -> Optional[Dict]:
        # sets are cool; two sets are disjoint if they have no keys in common. We
        # can use this to check whether these keys are in the solr result; if not,
        # we have no relationships to render, so we can return.
        if {'related_people_json', 'related_places_json', 'related_institutions_json'}.isdisjoint(obj.keys()):
            return None

        req = self.context.get("request")
        return RelationshipsSection(obj, context={"request": req}).data

    def get_incipits(self, obj: SolrResult) -> Optional[Dict]:
        if not obj.get("has_incipits_b"):
            return None

        req = self.context.get("request")
        return IncipitsSection(obj, context={"request": req}).data

    def get_references_notes(self, obj: SolrResult) -> Optional[Dict]:
        req = self.context.get("request")
        refnotes: Dict = ReferencesNotesSection(obj, context={"request": req}).data

        # if the only two keys in the references and notes section is 'label' and 'type'
        # then there is no content and we can hide this section.
        if not {'label', 'type'}.isdisjoint(refnotes.keys()):
            return None

        return refnotes

    def get_works(self, obj: SolrResult) -> Optional[Dict]:
        req = self.context.get("request")
        wks: Dict = WorksSection(obj, context={"request": req}).data
        if 'items' not in wks:
            return None

        return wks

    def get_exemplars(self, obj: SolrResult) -> Optional[Dict]:
        req = self.context.get("request")
        exmplrs: Dict = ExemplarsSection(obj, context={"request": req}).data
        if 'items' not in exmplrs:
            return None

        return exmplrs

    def get_items(self, obj: SolrResult) -> Optional[Dict]:
        req = self.context.get("request")
        itms: Dict = SourceItemsSection(obj, context={"request": req}).data
        if 'items' not in itms:
            return None

        return itms
