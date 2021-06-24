from typing import Dict, List

import serpy
from small_asc.client import Results

from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection


async def handle_front_request(req) -> Dict:
    return Front({}, context={"request": req, "direct_request": True}).data


class Front(JSONLDContextDictSerializer):
    fid = serpy.MethodField(
        label="id"
    )
    ftype = StaticField(
        label="type",
        value="rism:Root"
    )
    stats = serpy.MethodField()
    endpoints = serpy.MethodField()

    def get_fid(self, obj: Dict) -> str:
        req = self.context.get("request")

        return get_identifier(req, "root")

    def get_stats(self, obj: Dict) -> List[Dict]:
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        rq = {
            "facet.field": "{!terms='source,person,institution,incipit'}type",
            "rows": 0,
            "facet": "on"
        }
        res: Results = SolrConnection.search({"params": {"q": "*:*", **rq}})
        fields = res.facets['facet_fields']

        # These two lines take a Solr facet list, which looks like
        # ["foo", 22, "bar", 20, "baz", 18] and turn it into a list
        # like [("foo", 22), ("bar", 20), ("baz", 18) which can easily be turned into a dictionary.
        v_iter = iter(fields.get("type", []))
        zipped_list = zip(v_iter, v_iter)

        field_config: LabelConfig = {
            "source": ("records.source", None),  # TODO: "Sources" once added to translations
            "institution": ("records.institutions", None),
            "person": ("records.person", None),  # TODO: "People" once added to translations
            "incipit": ("records.incipits", None),
        }

        return get_display_fields(dict(zipped_list), transl, field_config)

    def get_endpoints(self, obj: Dict) -> List:
        req = self.context.get("request")
        return [
            get_identifier(req, "search")
        ]
