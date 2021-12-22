from typing import Optional

from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.sources.full_source import FullSource


async def handle_source_request(req, source_id: str) -> Optional[dict]:
    source_record: Optional[dict] = SolrConnection.get(f"source_{source_id}")

    if not source_record:
        return None

    return FullSource(source_record, context={"request": req,
                                              "direct_request": True}).data
