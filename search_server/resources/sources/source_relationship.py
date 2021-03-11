import logging
import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier, RELATIONSHIP_LABELS, RISM_JSONLD_CONTEXT, \
    get_jsonld_context, JSONLDContext, QUALIFIER_LABELS
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection, SolrResult, SolrManager

log = logging.getLogger()


def handle_relationships_list_request(req, source_id: str) -> Optional[Dict]:
    pass


def handle_relationships_request(req, source_id: str, relationship_id: str) -> Optional[Dict]:
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


class SourceRelationshipList(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )

    mid = serpy.MethodField(
        label="id"
    )
    rtype = StaticField(
        label="type",
        value="rism:RelationshipList"
    )
    label = serpy.MethodField()
    items = serpy.MethodField()

    def get_ctx(self, obj: SolrResult) -> Optional[Dict]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_mid(self, obj: SolrResult) -> str:
        req = self.context.get("request")
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "relationships_list", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return transl.get("records.people_institutions")

    def get_items(self, obj: SolrResult) -> Optional[List[Dict]]:
        relationships: Optional[List] = obj.get("relationships_json")
        if not relationships:
            return None

        relationship_list = SourceRelationship(relationships, many=True,
                                               context={"request": self.context.get("request")})

        return relationship_list.data


class SourceRelationship(ContextDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    srid = serpy.MethodField(
        label="id"
    )
    rtype = StaticField(
        label="type",
        value="rism:SourceRelationship"
    )
    role = serpy.MethodField()
    qualifier = serpy.MethodField()

    related_to = serpy.MethodField(
        label="relatedTo"
    )

    def get_ctx(self, obj: Dict) -> Optional[JSONLDContext]:
        direct_request: bool = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get("request")

        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        relationship_id: str = f"{obj.get('relationship_id')}"

        return get_identifier(req, "relationship", source_id=source_id, relationship_id=relationship_id)

    def get_role(self, obj: Dict) -> Optional[Dict]:
        relator: Optional[str] = obj.get("relationship_s")
        if not relator:
            return None

        req = self.context.get("request")
        transl: Dict = req.app.translations

        translation_key: str = RELATIONSHIP_LABELS.get(relator)

        return {
            "type": f"relators:{relator}",
            "label": transl.get(translation_key)
        }

    def get_qualifier(self, obj: Dict) -> Optional[Dict]:
        qualifier: Optional[str] = obj.get('qualifier_s')
        if not qualifier:
            return None

        req = self.context.get("request")
        transl: Dict = req.app.translations

        translation_key: str = QUALIFIER_LABELS.get(qualifier)

        return {
            "type": f"rismdata:{qualifier}",
            "label": transl.get(translation_key)
        }

    def get_related_to(self, obj: Dict) -> Optional[Dict]:
        req = self.context.get("request")
        reltype = obj.get("type")

        identifer: str
        name: Dict

        if reltype == "source_person_relationship":
            person_id: str = re.sub(ID_SUB, "", obj.get("person_id"))
            objtype = "rism:Person"
            dates: Optional[str] = f" ({d})" if (d := obj.get("date_statement_s")) else ""
            name = {"none": [f"{obj.get('name_s')}{dates}"]}
            identifier = get_identifier(req, "person", person_id=person_id)
        else:
            # reltype is source_institution_identifier
            institution_id: str = re.sub(ID_SUB, "", obj.get("institution_id"))
            objtype = "rism:Institution"
            name = {"none": [obj.get("name_s")]}
            identifier = get_identifier(req, "institution", institution_id=institution_id)

        return {
            "id": identifier,
            "type": objtype,
            "label": name
        }
