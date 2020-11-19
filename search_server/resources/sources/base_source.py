import re
from typing import Dict, Optional, List

import serpy

from search_server.helpers.display_fields import get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.ld_context import RISM_JSONLD_CONTEXT
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class BaseSource(ContextDictSerializer):
    """
    A base source serializer for providing a basic set of information for
    a RISM Source. A full record of the source is provided by the full source
    serializer, which adds additional information to this
    """
    ctx = serpy.MethodField(
        label="@context",
    )

    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Source"
    )
    display = serpy.MethodField(
        label="display"
    )

    part_of = serpy.MethodField(
        label="partOf"
    )

    def get_ctx(self, obj: Dict) -> Dict:
        direct_request: Optional[bool] = self.context.get("direct_request")
        return RISM_JSONLD_CONTEXT if direct_request else None

    def get_sid(self, obj: Dict) -> str:
        req = self.context.get('request')
        source_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "source", source_id=source_id)

    def get_display(self, obj: SolrResult) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.translations

        return get_display_fields(obj, transl)

    def get_part_of(self, obj: Dict) -> Optional[List]:
        # Do not show 'partOf' if the result is embedded in the source it is part of.
        if not self.context.get("direct_request"):
            return None

        this_id: Optional[str] = obj.get("source_id")
        member_id: Optional[str] = obj.get("source_membership_id")

        # If either the source_id or member_id are missing, or if
        # they are the same value, then we don't have enough information
        # to show a 'partOf' relationship.
        if not this_id or not member_id or (this_id == member_id):
            return None

        req = self.context.get("request")
        rel_id: str = re.sub(ID_SUB, "", member_id)
        transl: Dict = req.app.translations

        return [{
            "id": get_identifier(req, "source", source_id=rel_id),
            "type": "rism:Source",
            "display": {
                "label": transl.get("records.parent_record"),
                "value": {"none": obj.get("source_membership_title_s")}
            }
        }]
