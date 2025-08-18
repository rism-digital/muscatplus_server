from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.works.full_work import FullWork


async def handle_work_request(req, work_id: str) -> dict | None:
    work_record: dict | None = await SolrConnection.get(f"work_{work_id}")  # type: ignore

    if not work_record:
        return None

    return await FullWork(
        work_record, context={"request": req, "direct_request": True}
    ).serialized


async def handle_work_search(req, work_id: str) -> dict | None:
    return {"works": "yeah"}
