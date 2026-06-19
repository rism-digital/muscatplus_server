from sanic import request
from sanic.log import logger
from small_asc.client import JsonAPIRequest, SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import SearchRequest
from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.inventories.inventory_item import InventoryItem
from search_server.resources.inventories.inventory_items_search import (
    InventoryItemResults,
)
from search_server.resources.search.base_search import serialize_response


async def handle_inventory_item_request(
    req, source_id: str, inventory_item_id: str
) -> dict | None:
    item_record: dict | None = await SolrConnection.get(
        f"inventory_item_{inventory_item_id}"
    )

    if not item_record:
        return None

    return await InventoryItem(
        item_record, context={"request": req, "direct_request": True}
    ).serialized


def _prepare_query(
    req, source_id: str, probe: bool = False
) -> tuple[JsonAPIRequest, dict | None]:
    try:
        request_compiler = SearchRequest(req, probe=probe)
        request_compiler.filters += [
            "type:inventory_item",
            f"source_id:source_{source_id}",
        ]
        request_compiler.sorts = ["source_order_i asc"]
        solr_params: JsonAPIRequest = request_compiler.compile()
    except InvalidQueryException as e:
        logger.exception("Invalid query: %s", e)
        raise

    return solr_params, request_compiler.query_report


async def handle_inventory_item_search_request(req, source_id: str) -> dict:
    try:
        solr_params, query_report = _prepare_query(req, source_id)
    except InvalidQueryException:
        raise

    extra_context: dict = {
        "direct_request": True,
        "query_validation": query_report,
    }

    try:
        result_data: dict = await serialize_response(
            req, solr_params, InventoryItemResults, extra_context
        )
    except SolrError:
        raise

    return result_data


async def handle_inventory_item_probe_request(
    req: request.Request, source_id: str
) -> dict:
    try:
        solr_params, query_report = _prepare_query(req, source_id, probe=True)
    except InvalidQueryException:
        raise

    extra_context: dict = {
        "direct_request": True,
        "probe_request": True,
        "query_validation": query_report,
    }

    try:
        result_data: dict = await serialize_response(
            req,
            solr_params,
            InventoryItemResults,
            extra_context,
        )
    except SolrError:
        raise

    return result_data
