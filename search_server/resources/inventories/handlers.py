from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.inventories.inventory_item import (
    InventoryItem,
    InventoryItemSection,
)


async def handle_inventory_items_list_request(req, source_id: str) -> dict | None:
    inventory_record: dict | None = await SolrConnection.get(f"source_{source_id}")

    if not inventory_record:
        return None

    return await InventoryItemSection(
        inventory_record, context={"request": req, "direct_request": True}
    ).serialized


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
