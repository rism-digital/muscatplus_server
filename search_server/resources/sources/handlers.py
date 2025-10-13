from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.sources.exemplars import ExemplarsSection, Holding
from search_server.resources.sources.full_source import FullSource


async def handle_source_request(req, source_id: str) -> dict | None:
    source_record: dict | None = await SolrConnection.get(f"source_{source_id}")  # type: ignore

    if not source_record:
        return None

    return await FullSource(
        source_record, context={"request": req, "direct_request": True}
    ).serialized


async def handle_exemplar_section_request(req, source_id: str) -> dict | None:
    source_record: dict | None = await SolrConnection.get(f"source_{source_id}")  # type: ignore

    if not source_record:
        return None

    return await ExemplarsSection(
        source_record, context={"request": req, "direct_request": True}
    ).serialized


async def handle_holdings_request(req, source_id: str, holding_id: str) -> dict | None:
    holding_record: dict | None = await SolrConnection.get(f"holding_{holding_id}")  # type: ignore

    if not holding_record:
        # MSS records are assigned a holding ID comprised of the institution ID and the source ID. If
        # a direct lookup doesn't find anything, check to see if it's a MSS holding we're looking for.
        holding_record = await SolrConnection.get(  # type: ignore
            f"holding_{holding_id}-source_{source_id}"
        )

    if not holding_record:
        # It really doesn't exist.
        return None

    return await Holding(
        holding_record, context={"request": req, "direct_request": True}
    ).serialized
