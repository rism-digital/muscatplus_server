from search_server.resources.publications.publication import Publication
from shared_helpers.solr_connection import SolrConnection


async def handle_publication_request(req, publication_id: str) -> dict | None:
    publication_record: dict | None = await SolrConnection.get(f"publication_{publication_id}")  # type: ignore

    if not publication_record:
        return None

    return await Publication(publication_record, context={"request": req, "direct_request": True}).serialized


async def handle_publication_search_request(req, publication_id: str) -> dict:
    return {}
