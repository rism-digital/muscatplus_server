import ypres
from sanic import request

from search_server.helpers.identifiers import get_identifier
from search_server.helpers.solr_connection import SolrConnection, SolrResult


async def handle_tombstone(req: request.Request) -> dict | None:
    match_info = req.match_info
    route_name: str | None = req.route.name if req.route else None
    if not route_name:
        return None

    record_id: str

    match route_name:
        case "mp_server.sources.source":
            # source lookup
            source_id = match_info.get("source_id")
            if not source_id:
                return None
            record_id = f"tombstone_source_{source_id}"
        case "mp_server.sources.holding":
            holding_id = match_info.get("holding_id")
            if not holding_id:
                return None
            record_id = f"tombstone_holding_{holding_id}"
        case "mp_server.people.person":
            person_id = match_info.get("person_id")
            if not person_id:
                return None
            record_id = f"tombstone_person_{person_id}"
        case "mp_server.institutions.institution":
            institution_id = match_info.get("institution_id")
            if not institution_id:
                return None
            record_id = f"tombstone_institution_{institution_id}"
        case _:
            return None

    tombstone_record: dict | None = await SolrConnection.get(record_id)  # type: ignore
    if not tombstone_record:
        return None

    return Tombstone(tombstone_record, context={"request": req}).serialized


class Tombstone(ypres.DictSerializer):
    tid = ypres.MethodField(label="id")
    ttype = ypres.StaticField(label="type", value="rism:Tombstone")
    rtype = ypres.MethodField(label="recordType")
    tname = ypres.MethodField(label="name", required=False)
    deleted = ypres.StrField(attr="removed_dt", required=False)

    def get_tid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        tombstone_type = obj["record_type_s"]
        record_id = obj["record_id"]
        match tombstone_type:
            case "source":
                return get_identifier(req, "sources.source", source_id=record_id)
            case "holding":
                return ""  # TODO: Extract from "name" and create full URL.
            case "person":
                return get_identifier(req, "people.person", person_id=record_id)
            case "institution":
                return get_identifier(
                    req, "institutions.institution", institution_id=record_id
                )
            case _:
                return ""

    def get_tname(self, obj: SolrResult) -> dict:
        return {"none": [obj["display_name_s"]]}

    def get_rtype(self, obj: SolrResult) -> str:
        match obj["record_type_s"]:
            case "source":
                return "rism:Source"
            case "person":
                return "rism:Person"
            case "institution":
                return "rism:Institution"
            case "holding":
                return "rism:Holding"
            case _:
                return "rism:Unknown"
