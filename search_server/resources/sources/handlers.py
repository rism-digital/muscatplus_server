
from search_server.resources.sources.full_source import FullSource
from shared_helpers.solr_connection import SolrConnection


async def handle_source_request(req, source_id: str) -> dict | None:
    source_record: dict | None = await SolrConnection.get(f"source_{source_id}")  # type: ignore

    if not source_record:
        return None

    return await FullSource(
        source_record, context={"request": req, "direct_request": True}
    ).serialized
