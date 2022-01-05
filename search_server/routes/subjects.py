from sanic import Blueprint

from search_server.request_handlers import handle_request, handle_search
from search_server.resources.subjects.subject import handle_subject_request
from search_server.resources.subjects.subject_source import handle_subject_source_request

subjects_blueprint: Blueprint = Blueprint("subjects", url_prefix="/subjects")


@subjects_blueprint.route("/")
async def subject_list(req):
    pass


@subjects_blueprint.route("/<subject_id:str>/")
async def subject(req, subject_id: str):
    return await handle_request(req,
                                handle_subject_request,
                                subject_id=subject_id)


@subjects_blueprint.route("/<subject_id:str>/sources/")
async def subject_sources(req, subject_id: str):
    return await handle_search(req,
                               handle_subject_source_request,
                               subject_id=subject_id)
