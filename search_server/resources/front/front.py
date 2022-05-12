import serpy
from sanic import response
from small_asc.client import Results

from search_server.exceptions import InvalidQueryException
from shared_helpers.fields import StaticField
from shared_helpers.identifiers import get_identifier
from search_server.helpers.search_request import SearchRequest
from shared_helpers.serializers import JSONLDContextDictSerializer
from shared_helpers.solr_connection import SolrConnection
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
    endpoints = serpy.MethodField()
    facets = serpy.MethodField()

    def get_fid(self, obj: Results) -> str:
        req = self.context.get("request")

        return get_identifier(req, "front")

    def get_endpoints(self, obj: Results) -> list:
        req = self.context.get("request")
        return [
            get_identifier(req, "query.search")
        ]

    def get_facets(self, obj: Results) -> dict:
        req = self.context.get("request")
        return get_facets(req, obj)
