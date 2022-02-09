import serpy
from sanic import response
from small_asc.client import Results

from search_server.exceptions import InvalidQueryException
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import get_identifier
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.facets import get_facets


async def handle_front_request(req) -> response.HTTPResponse:
    try:
        request_compiler: SearchRequest = SearchRequest(req, probe=True)
        solr_params: dict = request_compiler.compile()
    except InvalidQueryException as e:
        return response.text(f"Invalid search query. {e}", status=400)

    solr_res: Results = SolrConnection.search(solr_params)

    results: dict = Front(solr_res,
                          context={"request": req, "direct_request": True}).data

    response_headers: dict = {
        "Content-Type": "application/ld+json; charset=utf-8"
    }

    return response.json(
        results,
        headers=response_headers,
        escape_forward_slashes=False,
        indent=(4 if req.app.ctx.config['common']['debug'] else 0)
    )


class Front(JSONLDContextDictSerializer):
    fid = serpy.MethodField(
        label="id"
    )
    ftype = StaticField(
        label="type",
        value="rism:Front"
    )
    stats = serpy.MethodField()
    endpoints = serpy.MethodField()
    facets = serpy.MethodField()

    def get_fid(self, obj: dict) -> str:
        req = self.context.get("request")

        return get_identifier(req, "front")

    def get_stats(self, obj: dict) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

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

        facet_numbers: dict = dict(zipped_list)

        return {
            "sources": {
                "label": transl.get("records.sources"),
                "value": facet_numbers.get("source", 0)
            },
            "institutions": {
                "label": transl.get("records.institutions"),
                "value": facet_numbers.get("institution", 0)
            },
            "people": {
                "label": transl.get("records.people"),
                "value": facet_numbers.get("person", 0)
            },
            "incipits": {
                "label": transl.get("records.incipits"),
                "value": facet_numbers.get("incipit", 0)
            }
        }

    def get_endpoints(self, obj: dict) -> list:
        req = self.context.get("request")
        return [
            get_identifier(req, "query.search")
        ]

    def get_facets(self, obj: Results) -> dict:
        req = self.context.get("request")
        return get_facets(req, obj)
