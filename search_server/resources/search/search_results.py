import re
from typing import Dict, Optional, List

import pysolr
import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import (
    get_identifier,
    get_jsonld_context,
    JSONLDContext,
    ID_SUB
)
from search_server.helpers.serializers import ContextDictSerializer, ContextSerializer
from search_server.resources.search.pagination import Pagination


class SearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = serpy.MethodField(
        label="type"
    )
    summary = serpy.MethodField()

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        if obj["type"] == "source":
            kwargs = {"source_id": id_value}
        elif obj["type"] == "person":
            kwargs = {"person_id": id_value}
        elif obj["type"] == "institution":
            kwargs = {"institution_id": id_value}

        return get_identifier(req, obj.get("type"), **kwargs)

    def get_label(self, obj: Dict) -> Dict:
        label: str

        if obj["type"] == "source":
            label = obj.get("main_title_s")
        elif obj["type"] == "person" or obj['type'] == "institution":
            label = obj.get("name_s")
        else:
            label = "[ Test Title ]"

        return {"none": [label]}

    def get_result_type(self, obj: Dict) -> str:
        return f"rism:{obj.get('type').title()}"

    def get_summary(self, obj: Dict) -> List[Dict]:
        return [{
            "label": {"en": ["A label"]},
            "value": {"none": ["A value"]}
        }, {
            "label": {"de": ["A German label"]},
            "value": {"none": ["A German value"]}
        }]



class SearchResults(ContextSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )
    sid = serpy.MethodField(
        label="id"
    )
    stype = StaticField(
        label="type",
        value="Collection"
    )
    total_items = serpy.MethodField(
        label="totalItems"
    )
    view = serpy.MethodField()
    items = serpy.MethodField()

    def get_ctx(self, obj: pysolr.Results) -> JSONLDContext:
        return get_jsonld_context(self.context.get("request"))

    def get_sid(self, obj: pysolr.Results) -> str:
        req = self.context.get('request')

        return get_identifier(req, "search", **req.args)

    def get_total_items(self, obj: pysolr.Results) -> int:
        return obj.hits

    def get_view(self, obj: pysolr.Results) -> Dict:
        p = Pagination(obj, context={"request": self.context.get('request')})
        return p.data

    def get_items(self, obj: pysolr.Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return SearchResult(obj.docs, many=True, context={"request": self.context.get("request")}).data
