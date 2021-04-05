import logging
import re
from typing import Dict, List, Optional

import pysolr
import serpy

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrManager, SolrResult, has_results
from search_server.resources.shared.external_link import ExternalResourcesList
from search_server.resources.shared.institution_relationship import InstitutionRelationshipList, InstitutionRelationship
from search_server.resources.shared.person_relationship import PersonRelationshipList, PersonRelationship
from search_server.resources.sources.base_source import BaseSource
from search_server.resources.sources.source_exemplar import SourceExemplarList
from search_server.resources.sources.source_incipit import SourceIncipitList
from search_server.resources.sources.source_materialgroup import SourceMaterialGroupList
from search_server.resources.sources.source_note import SourceNoteList
from search_server.resources.sources.source_subject import SourceSubject

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

    return PersonRelationship(target_relationship[0], context={"request": req,
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

    return InstitutionRelationship(target_relationship[0], context={"request": req,
                                                                    "direct_request": True}).data


def handle_creator_request(req, source_id: str) -> Optional[Dict]:
    source_record: Optional[Dict] = _source_lookup(source_id)
    if not source_record:
        return None

    if 'creator_json' not in source_record:
        return None

    creator = source_record['creator_json'][0]

    return PersonRelationship(creator, context={"request": req,
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
        transl: Dict = req.app.translations

        return transl.get("records.items_in_source")


class FullSource(BaseSource):
    summary = serpy.MethodField()
    creator = serpy.MethodField()
    related = serpy.MethodField()
    materials = serpy.MethodField()
    subjects = serpy.MethodField()
    notes = serpy.MethodField()
    exemplars = serpy.MethodField()
    incipits = serpy.MethodField()
    external_links = serpy.MethodField(
        label="externalLinks"
    )
    items = serpy.MethodField()

    def get_summary(self, obj: SolrResult) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return get_display_fields(obj, transl)

    def get_creator(self, obj: SolrResult) -> Optional[Dict]:
        if 'creator_json' not in obj:
            return None

        return PersonRelationship(obj["creator_json"][0],
                                  context={"request": self.context.get('request')}).data

    def get_related(self, obj: SolrResult) -> Optional[Dict]:
        items: List = []
        req = self.context.get("request")

        if 'related_people_json' in obj:
            items.append(
                PersonRelationshipList(obj,
                                       context={"request": req}).data
            )

        if 'related_institutions_json' in obj:
            items.append(
                InstitutionRelationshipList(obj,
                                            context={"request": req}).data
            )

        if not items:
            return None

        transl: Dict = req.app.translations

        return {
            "type": "rism:Relations",
            "label": transl.get("records.relations"),
            "items": items
        }

    def get_materials(self, obj: SolrResult) -> Optional[Dict]:
        if 'material_groups_json' not in obj:
            return None

        return SourceMaterialGroupList(obj,
                                       context={"request": self.context.get('request')}).data

    def get_subjects(self, obj: SolrResult) -> Optional[List]:
        if 'subjects_json' not in obj:
            return None

        subjects = SourceSubject(obj['subjects_json'],
                                 many=True,
                                 context={"request": self.context.get("request")})

        return subjects.data

    def get_notes(self, obj: SolrResult) -> Optional[List]:
        # This does not perform an extra Solr lookup to get the notes, so we can just render it and then
        # look to see if anything came back.
        notelist = SourceNoteList(obj, context={"request": self.context.get("request")}).data

        # Check to see if any notes were actually rendered; if not, return None
        if 'items' not in notelist:
            return None

        return notelist

    def get_exemplars(self, obj: SolrResult) -> Optional[List[Dict]]:
        """
        Exemplars and "holding" are equivalent in Muscatese.
        :param obj:
        :return:
        """
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:holding"]

        if not has_results(fq=fq):
            return None

        return SourceExemplarList(obj, context={"request": self.context.get("request")}).data

    def get_incipits(self, obj: SolrResult) -> Optional[Dict]:
        fq: List = [f"source_id:{obj.get('id')}",
                    "type:source_incipit"]
        if not has_results(fq=fq):
            return None

        return SourceIncipitList(obj, context={"request": self.context.get("request")}).data

    def get_external_links(self, obj: SolrResult) -> Optional[Dict]:
        if 'external_links_json' not in obj:
            return None

        return ExternalResourcesList(obj, context={"request": self.context.get("request")}).data

    def get_items(self, obj: SolrResult) -> Optional[List]:
        this_id: str = obj.get("source_id")

        # Remember to filter out the current source from the list of all sources in this membership group.
        fq: List = ["type:source",
                    f"source_membership_id:{this_id}",
                    f"!source_id:{this_id}"]
        sort: str = "source_id asc"

        if not has_results(fq=fq):
            return None

        conn = SolrManager(SolrConnection)
        # increasing the number of rows means fewer requests for larger items, but NB: Solr pre-allocates memory
        # for each value in row, so there needs to be a balance between large numbers and fewer requests.
        # (remember that the SolrManager object automatically retrieves the next page of results when iterating)
        conn.search("*:*", fq=fq, sort=sort, rows=100)

        sources = BaseSource(conn.results, many=True,
                             context={"request": self.context.get("request")})

        return sources.data
