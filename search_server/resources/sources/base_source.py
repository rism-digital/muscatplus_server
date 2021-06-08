import re
from typing import Dict, Optional, List

import serpy

from search_server.helpers.display_fields import LabelConfig, get_display_fields
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import ID_SUB, get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.record_history import get_record_history


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
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    label = serpy.MethodField()
    part_of = serpy.MethodField(
        label="partOf"
    )
    summary = serpy.MethodField()
    record_history = serpy.MethodField(
        label="recordHistory"
    )

    def get_sid(self, obj: Dict) -> str:
        req = self.context.get('request')
        source_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "sources.source", source_id=source_id)

    def get_label(self, obj: SolrResult) -> Dict:
        return {
            "none": [obj.get("main_title_s")]
        }

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.source")

    def get_part_of(self, obj: Dict) -> Optional[Dict]:
        # This source is not part of another source; return None
        if 'source_membership_json' not in obj:
            return None

        source_membership: Dict = obj.get('source_membership_json', {})

        req = self.context.get('request')
        parent_source_id: str = re.sub(ID_SUB, "", source_membership.get("source_id"))
        ident: str = get_identifier(req, "sources.source", source_id=parent_source_id)
        transl = req.app.ctx.translations

        parent_title: Optional[str] = source_membership.get("main_title")

        return {
            "label": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": ident,
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "label": {"none": [parent_title]}
            }
        }

    # This method will get overridden in the 'full source' class, and will be returned as 'None' since
    # the summary is part of the 'contents' section. But in the base source view it will deliver some basic
    # identification fields.
    def get_summary(self, obj: Dict) -> Optional[List[Dict]]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        field_config: LabelConfig = {
            "creator_name_s": ("records.composer_author", None),
            "source_type_sm": ("records.source_type", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)

    def get_record_history(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return get_record_history(obj, transl)
