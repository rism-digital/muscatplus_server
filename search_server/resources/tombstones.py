import ypres
from sanic import request
from small_asc.client import Results

from shared_helpers.identifiers import get_identifier
from shared_helpers.solr_connection import SolrConnection, SolrResult


async def handle_tombstone(req: request.Request) -> dict | None:
    match_info = req.match_info
    route_name: str | None = req.route.name if req.route else None
    if not route_name:
        return None

    fq: list = ["type:tombstone"]

    match route_name:
        case "mp_server.sources.source":
            # source lookup
            source_id = match_info.get("source_id")
            if not source_id:
                return None
            fq += ["record_type_s:source", f"record_id:{source_id}"]
        case "mp_server.sources.holding":
            holding_id = match_info.get("holding_id")
            if not holding_id:
                return None
            fq += ["record_type_s:holding", f"record_id:{holding_id}"]
        case "mp_server.people.person":
            person_id = match_info.get("person_id")
            if not person_id:
                return None
            fq += ["record_type_s:person", f"record_id:{person_id}"]
        case "mp_server.institutions.institution":
            institution_id = match_info.get("institution_id")
            if not institution_id:
                return None
            fq += ["record_type_s:institution", f"record_id:{institution_id}"]
        case _:
            return None

    tombstone_q: Results = await SolrConnection.search({"query": "*:*", "filter": fq})
    if tombstone_q.hits == 0:
        return None

    return Tombstone(tombstone_q.docs[0], context={"request": req}).serialized


class Tombstone(ypres.DictSerializer):
    tid = ypres.MethodField(label="id")
    ttype = ypres.StaticField(label="type",
                              value="rism:Tombstone")
    rtype = ypres.MethodField(label="recordType")
    tname = ypres.MethodField(label="name",
                              required=False)
    deleted = ypres.StrField(attr="removed_dt",
                             required=False)

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
                return get_identifier(req, "institutions.institution", institution_id=record_id)
            case _:
                return ""

    def get_tname(self, obj: SolrResult) -> dict:
        return { "none": [obj["display_name_s"]]}

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
