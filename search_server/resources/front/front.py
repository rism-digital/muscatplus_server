import orjson
import ypres
from sanic import response
from small_asc.client import JsonAPIRequest, Results

from search_server.exceptions import InvalidQueryException
from search_server.helpers.identifiers import get_identifier
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.facets import get_facets
from search_server.template_render import render_template


async def handle_front_request(req) -> response.HTTPResponse:
    try:
        request_compiler: SearchRequest = SearchRequest(req, probe=True)
        solr_params: JsonAPIRequest = request_compiler.compile()
    except InvalidQueryException as e:
        return response.json({"message": f"Invalid search query. {e}"}, status=400)

    solr_res: Results = await SolrConnection.search(solr_params)

    results: dict = Front(
        solr_res, context={"request": req, "direct_request": True}
    ).serialized

    accept: str | None = req.headers.get("Accept")
    app_context = req.app.ctx

    if accept and "json" in accept:
        return response.json(
            results,
            content_type="application/ld+json;charset=utf-8",
            option=orjson.OPT_INDENT_2 if req.app.ctx.config["common"]["debug"] else 0,
        )
    else:
        rendered_template: str = render_template(app_context, req, results)
        return response.html(rendered_template)


class Front(ypres.DictSerializer):
    fid = ypres.MethodField(label="id")
    ftype = ypres.StaticField(label="type", value="rism:Front")
    endpoints = ypres.MethodField()
    facets = ypres.MethodField()
    query_fields = ypres.MethodField(label="queryFields")

    def get_fid(self, obj: Results) -> str:
        req = self.context["request"]

        return get_identifier(req, "front")

    def get_endpoints(self, obj: Results) -> list:
        req = self.context["request"]
        return [get_identifier(req, "query.search")]

    def get_facets(self, obj: Results) -> dict | None:
        req = self.context["request"]
        return get_facets(req, obj)

    def get_query_fields(self, obj: Results) -> list | None:
        req = self.context["request"]
        cfg: dict = req.app.ctx.config
        transl: dict = req.app.ctx.translations

        current_mode: str = req.args.get("mode", cfg["search"]["default_mode"])
        qfields: list = cfg["search"]["modes"][current_mode].get("q_fields", [])

        query_fields: list = []

        for qfield in qfields:
            q_translation_key: str = qfield["label"]
            q_translation: dict | None = transl.get(q_translation_key)
            q_label: dict = q_translation or {"none": [q_translation_key]}
            query_fields.append(
                {
                    "label": q_label,
                    "alias": qfield["alias"],
                }
            )

        return query_fields or None
