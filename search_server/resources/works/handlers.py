from typing import Optional

from search_server.resources.works.full_work import FullWork
from shared_helpers.solr_connection import SolrConnection


async def handle_work_request(req, work_id: str) -> Optional[dict]:
    work_record: Optional[dict] = await SolrConnection.get(f"work_{work_id}")

    if not work_record:
        return None

    return await FullWork(
        work_record, context={"request": req, "direct_request": True}
    ).data
