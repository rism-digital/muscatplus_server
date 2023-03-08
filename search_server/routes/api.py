from sanic import Blueprint, response

from shared_helpers.jsonld import (
    RISM_JSONLD_DEFAULT_CONTEXT,
    RISM_JSONLD_WORK_CONTEXT,
    RISM_JSONLD_PERSON_CONTEXT,
    RISM_JSONLD_SOURCE_CONTEXT)

api_blueprint: Blueprint = Blueprint("api", url_prefix="/api/v1")


@api_blueprint.route("/source.json")
async def source_context(req) -> response.HTTPResponse:
    return response.json({"@context": RISM_JSONLD_SOURCE_CONTEXT})


@api_blueprint.route("/person.json")
async def person_context(req) -> response.HTTPResponse:
    return response.json({"@context": RISM_JSONLD_PERSON_CONTEXT})


@api_blueprint.route("/work.json")
async def work_context(req) -> response.HTTPResponse:
    return response.json({"@context": RISM_JSONLD_WORK_CONTEXT})


@api_blueprint.route("/context.json")
async def default_context(req) -> response.HTTPResponse:
    return response.json({"@context": RISM_JSONLD_DEFAULT_CONTEXT})