from search_server.request_handlers import handle_search_request, handle_request
from search_server.resources.sources.full_source import handle_source_request
from search_server.resources.sources.source_creator import handle_creator_request
from search_server.resources.sources.source_exemplar import handle_holding_request
from search_server.resources.sources.source_incipit import handle_incipits_list_request, handle_incipit_request
from search_server.resources.sources.source_list import handle_source_list_request
from search_server.resources.sources.source_materialgroup import handle_materialgroups_list_request, \
    handle_materialgroups_request
from search_server.resources.sources.source_relationship import handle_relationships_list_request, \
    handle_relationships_request

from sanic import Blueprint

sources_blueprint: Blueprint = Blueprint("sources", url_prefix="/sources")


@sources_blueprint.route("/")
async def source_list(req):
    return await handle_search_request(req,
                                       handle_source_list_request)


@sources_blueprint.route("/<source_id:string>/")
async def source(req, source_id: str):
    return await handle_request(req,
                                 handle_source_request,
                                 source_id=source_id)


@sources_blueprint.route("/<source_id:string>/incipits/")
async def incipits_list(req, source_id: str):
    return await handle_request(req,
                                 handle_incipits_list_request,
                                 source_id=source_id)


@sources_blueprint.route("/<source_id:string>/incipits/<work_num:string>/")
async def incipit(req, source_id: str, work_num: str):
    return await handle_request(req,
                                 handle_incipit_request,
                                 source_id=source_id,
                                 work_num=work_num)


@sources_blueprint.route("/<source_id:string>/materialgroups/")
async def materialgroups_list(req, source_id: str):
    return await handle_request(req,
                                 handle_materialgroups_list_request,
                                 source_id=source_id)


@sources_blueprint.route("/<source_id:string>/materialgroups/<materialgroup_id:string>/")
async def materialgroup(req, source_id: str, materialgroup_id: str):
    return await handle_request(req,
                                 handle_materialgroups_request,
                                 source_id=source_id,
                                 materialgroup_id=materialgroup_id)


@sources_blueprint.route("/<source_id:string>/relationships/")
async def relationships_list(req, source_id: str):
    return await handle_request(req,
                                 handle_relationships_list_request,
                                 source_id=source_id)


@sources_blueprint.route("/<source_id:string>/relationships/<relationship_id:string>/")
async def relationship(req, source_id: str, relationship_id: str):
    return await handle_request(req,
                                 handle_relationships_request,
                                 source_id=source_id,
                                 relationship_id=relationship_id)


@sources_blueprint.route("/<source_id:string>/creator")
async def creator(req, source_id: str):
    return await handle_request(req,
                                 handle_creator_request,
                                 source_id=source_id)


@sources_blueprint.route("/<source_id:string>/holdings/")
async def holding_list(req, source_id: str):
    pass


@sources_blueprint.route("/<source_id:string>/holdings/<holding_id:string>/")
async def holding(req, source_id: str, holding_id: str):
    return await handle_request(req,
                                 handle_holding_request,
                                 source_id=source_id,
                                 holding_id=holding_id)
