import re
from typing import Optional

import ypres

from shared_helpers.display_fields import LabelConfig, get_display_fields
from shared_helpers.identifiers import ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrConnection


async def handle_festival_request(req, festival_id: str) -> Optional[dict]:
    record: Optional[dict] = await SolrConnection.get(f"id:festival_{festival_id}")

    if not record:
        return None

    return LiturgicalFestival(
        record, context={"request": req, "direct_request": True}
    ).data


class LiturgicalFestival(ypres.DictSerializer):
    fid = ypres.MethodField(label="id")
    ftype = ypres.StaticField(label="type", value="rism:LiturgicalFestival")
    label = ypres.MethodField()
    summary = ypres.MethodField()

    def get_fid(self, obj: dict) -> str:
        req = self.context.get("request")
        festival_id: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "festivals.festival", festival_id=festival_id)

    def get_label(self, obj: dict) -> dict:
        # This serializer can also be used by the 'liturgical festival' section
        # on a source, which has a different name field.
        if "name" in obj:
            return {"none": [f"{obj.get('name')}"]}
        else:
            return {"none": [f"{obj.get('name_s')}"]}

    def get_summary(self, obj: dict) -> Optional[list]:
        if not self.context.get("direct_request"):
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        field_config: LabelConfig = {
            # should be "Alternate terms" but this is not available in the translations currently...
            "alternate_terms_sm": ("records.other_form_of_name", None),
            "notes_sm": ("records.general_note", None),
        }

        return get_display_fields(obj, transl, field_config=field_config)
