from sanic import Blueprint

from search_server.request_handlers import handle_request
from search_server.resources.incipits.incipit import handle_incipits_list_request, handle_incipit_request
from search_server.resources.sources.handlers import (
    handle_source_request,
    handle_people_relationships_list_request,
    handle_person_relationship_request,
    handle_institutions_relationships_list_request,
    handle_institution_relationship_request,
    handle_creator_request
)


sources_blueprint: Blueprint = Blueprint("sources", url_prefix="/sources")


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


@sources_blueprint.route("/<source_id:string>/material-groups/")
async def material_groups_list(req, source_id: str):
    return await handle_request(req,
                                handle_material_groups_list_request,
                                source_id=source_id)


@sources_blueprint.route("/<source_id:string>/material-groups/<material_id:string>/")
async def material_group(req, source_id: str, material_id: str):
    return await handle_request(req,
                                handle_material_group_request,
                                source_id=source_id,
                                materialgroup_id=material_id)


@sources_blueprint.route("/<source_id:string>/people/")
async def people_relationships_list(req, source_id: str):
    return await handle_request(req,
                                handle_people_relationships_list_request,
                                source_id=source_id)


@sources_blueprint.route("/<source_id:string>/people/<relationship_id:string>/")
async def person_relationship(req, source_id: str, relationship_id: str):
    return await handle_request(req,
                                handle_person_relationship_request,
                                source_id=source_id,
                                relationship_id=relationship_id)


@sources_blueprint.route("/<source_id:string>/institutions/")
async def institutions_relationships_list(req, source_id: str):
    return await handle_request(req,
                                handle_institutions_relationships_list_request,
                                source_id=source_id)


@sources_blueprint.route("/<source_id:string>/institutions/<relationship_id:string>/")
async def institution_relationship(req, source_id: str, relationship_id: str):
    return await handle_request(req,
                                handle_institution_relationship_request,
                                source_id=source_id,
                                relationship_id=relationship_id)


@sources_blueprint.route("/<source_id:string>/creator")
async def creator(req, source_id: str):
    return await handle_request(req,
                                handle_creator_request,
                                source_id=source_id)


@sources_blueprint.route("/<source_id:string>/exemplars/")
async def exemplar_list(req, source_id: str):
    pass


@sources_blueprint.route("/<source_id:string>/exemplars/<exemplar_id:string>/")
async def exemplar(req, source_id: str, exemplar_id: str):
    return await handle_request(req,
                                handle_exemplar_request,
                                source_id=source_id,
                                exemplar_id=exemplar_id)
