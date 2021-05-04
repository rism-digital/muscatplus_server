from typing import Dict, Optional, List

import pysolr

from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.shared.relationship import Relationship
from search_server.resources.sources.full_source import FullSource


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
