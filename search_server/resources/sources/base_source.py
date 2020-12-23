import re
from typing import Dict, Optional, List

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier, get_jsonld_context, \
    JSONLDContext
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
    label = serpy.MethodField()
    source_type = serpy.MethodField(
        label="sourceType"
    )
    part_of = serpy.MethodField(
        label="partOf"
    )

    def get_ctx(self, obj: Dict) -> Optional[JSONLDContext]:
        direct_request: Optional[bool] = self.context.get("direct_request")
        return get_jsonld_context(self.context.get("request")) if direct_request else None

    def get_sid(self, obj: Dict) -> str:
        req = self.context.get('request')
        source_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "source", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        return {
            "none": [obj.get("main_title_s")]
        }

    # TODO: Move translations of the source types to the locales
    #  and make this a proper language map.
    def get_source_type(self, obj: SolrResult) -> Dict:
        return {
            "none": [obj["subtype_s"]]
        }

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

        return [{
            "id": get_identifier(req, "source", source_id=rel_id),
            "type": "rism:Source",
            "label": {"none": [obj.get("source_membership_title_s")]}
        }]
