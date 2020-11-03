import logging
import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.ld_context import RISM_JSONLD_CONTEXT
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection

log = logging.getLogger()


def handle_relationship_request(req, source_id: str, relationship_id: str) -> Optional[Dict]:
    fq: List = [f"source_id:source_{source_id}",
                "type:source_person_relationship",
                f"relationship_id:{relationship_id}"]

    log.debug("Query: %s", fq)

    record: pysolr.Results = SolrConnection.search("*:*", fq=fq, rows=1)

    if record.hits == 0:
        return None

    relationship_record = record.docs[0]
    relationship = SourceRelationship(relationship_record, context={"request": req,
                                                                    "direct_request": True})

    return relationship.data


class SourceRelationship(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    srid = serpy.MethodField(
        label="id"
    )
    role = serpy.MethodField()
    qualifier = serpy.MethodField()
    related_to = serpy.MethodField(
        label="relatedTo"
    )

    def get_ctx(self, obj: Dict) -> Optional[Dict]:
        direct_request: bool = self.context.get("direct_request")
        return RISM_JSONLD_CONTEXT if direct_request else None

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get("request")

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        relationship_id: str = f"{obj.get('relationship_id')}"

        return get_identifier(req, "relationship", source_id=source_id, relationship_id=relationship_id)

    def get_role(self, obj: Dict) -> Optional[str]:
        if t := obj.get("relationship_s"):
            return f"relators:{t}"

        return None

    def get_qualifier(self, obj: Dict) -> str:
        return f"rism:{q}" if (q := obj.get('qualifier_s')) else None

    def get_related_to(self, obj: Dict) -> Optional[Dict]:
        req = self.context.get("request")
        reltype = obj.get("type")

        identifer: str

        if reltype == "source_person_relationship":
            person_id: str = re.sub(ID_SUB, "", obj.get("person_id"))
            objtype = "rism:Person"
            identifier = get_identifier(req, "person", person_id=person_id)
        else:
            # reltype is source_institution_identifier
            institution_id: str = re.sub(ID_SUB, "", obj.get("institution_id"))
            objtype = "rism:Institution"
            identifier = get_identifier(req, "institution", institution_id=institution_id)

        return {
            "id": identifier,
            "type": objtype,
            "name": {"none": [obj.get("name_s")]}
        }
