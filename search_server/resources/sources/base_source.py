import re
from typing import Dict, Optional

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class BaseSource(JSONLDContextDictSerializer):
    """
    A base source serializer for providing a basic set of information for
    a RISM Source. A full record of the source is provided by the full source
    serializer, which adds additional information to this
    """
    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="rism:Source"
    )
    label = serpy.MethodField()
    part_of = serpy.MethodField(
        label="partOf"
    )

    def get_sid(self, obj: Dict) -> str:
        req = self.context.get('request')
        source_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "sources.source", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        return {
            "none": [obj.get("main_title_s")]
        }

    def get_part_of(self, obj: Dict) -> Optional[Dict]:
        # This source is not part of another source; return None
        if 'source_membership_json' not in obj:
            return None

        # Do not show 'partOf' if the result is embedded in the source it is part of.
        if not self.context.get("direct_request"):
            return None

        source_membership: Dict = obj.get('source_membership_json', {})

        req = self.context.get('request')
        parent_source_id: str = re.sub(ID_SUB, "", source_membership.get("source_id"))
        ident: str = get_identifier(req, "sources.source", source_id=parent_source_id)

        parent_title: Optional[str] = source_membership.get("main_title")

        return {
            "id": ident,
            "type": "rism:Source",
            "label": {"none": [parent_title]}
        }
