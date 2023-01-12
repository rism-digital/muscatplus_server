import logging
import operator
import re
from collections import defaultdict
from typing import Optional

import serpy
from sanic import request, response
from small_asc.client import SolrError

from search_server.helpers.search_request import suggest_fields_for_alias
from search_server.request_handlers import send_json_response
from shared_helpers.serializers import JSONLDDictSerializer
from shared_helpers.solr_connection import SolrConnection

log = logging.getLogger(__name__)


class SuggestionResults(JSONLDDictSerializer):
    sid = serpy.MethodField(
        label="id"
    )
    typ = serpy.StaticField(
        label="type",
        value="rism:SuggestionResults"
    )
    alias = serpy.MethodField()
    items = serpy.MethodField()

    def get_sid(self, obj: dict) -> str:
        req = self.context.get("request")
        return req.url

    def get_alias(self, obj: dict) -> str:
        return self.context.get("alias")

    def get_items(self, obj: dict) -> list:
        """
        Handles the suggestions returned from Solr. Since we can specify multiple Solr fields
        for a single suggestion, this function will merge all the results from all the fields
        and return the top ones. This involves checking all the results, compiling them into a
        single results dictionary, sorting by the number of documents, and then taking the top
        N results, where N is set as a configuration parameter.

        The return value is a list of label/value pairs, where the value gives the count of the
        number returned.

        If no suggestions are found it will return a "no suggestions" result.

        :param obj: A Solr TermsComponent Result document
        :return: A list of label/value results. The count (value) is converted to a language map
            to make it easier to show in the UI (if needed).
        """
        req = self.context.get("request")
        cfg: dict = req.app.ctx.config
        num_suggestions: int = cfg['search']['suggestions']

        fields: list = self.context.get("suggest_fields")
        terms: dict = obj.get("terms", [])

        all_suggestions = defaultdict(int)
        for f in fields:
            suggest_for_field: list = terms.get(f, [])
            v_iter = iter(suggest_for_field)
            zipped_list = zip(v_iter, v_iter)
            for label, count in zipped_list:
                current_count = all_suggestions[label]
                all_suggestions[label] = current_count + count
        merged: dict = dict(all_suggestions)

        if len(merged) == 0:
            return [{
                "label": {"none": ["No suggestions"]},
                "value": 0
            }]

        res: list = []
        for label, value in sorted(merged.items(), key=operator.itemgetter(1), reverse=True):
            res.append({
                "label": {"none": [label]},
                "value": {"none": [f"{value}"]}
            })

        # Limit the number returned to the top N, where N is set in the configuration.
        return res[:num_suggestions]


async def handle_suggest_request(req: request.Request, **kwargs) -> response.HTTPResponse:
    alias: Optional[str] = req.args.get("alias")
    if not alias:
        return response.text("A suggest request requires an alias parameter", status=400)

    query: Optional[str] = req.args.get("q")
    if not query:
        return response.text("A suggest request requires a q parameter", status=400)

    cfg: dict = req.app.ctx.config
    # unlike the search handler we don't know what mode we're in, so we
    # have to process all facet definitions looking for the fields.
    facet_definitions: dict = cfg['search']['facet_definitions']
    field_map: dict = suggest_fields_for_alias(facet_definitions)
    fields: list = field_map.get(alias, [])

    # Since we will be using a regex, ensure any special characters are escaped before handing the
    # query off to Solr.
    escaped_query: str = re.escape(query)

    try:
        solr_res: dict = await SolrConnection.term_suggest({"query": escaped_query, "fields": fields})
    except SolrError:
        msg: str = "Error sending suggest request"
        log.exception(msg)
        return response.text(msg, status=500)

    suggest_results: dict = SuggestionResults(solr_res,
                                              context={"request": req,
                                                       "alias": alias,
                                                       "direct_request": True,
                                                       "suggest_fields": fields}).data

    return await send_json_response(suggest_results, req.app.ctx.config['common']['debug'])
