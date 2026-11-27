"""HTTP surface for IIIF Presentation 3 Collections."""

from sanic import Blueprint, response
from sanic.exceptions import SanicException
from sanic.log import logger
from small_asc.client import SolrError

from search_server.helpers.identifiers import get_site
from search_server.negotiation import negotiate_media_type
from search_server.resources.iiif.collections import (
    IIIF_CONTEXT,
    build_institution,
    build_material,
    build_root,
)

iiif_blueprint = Blueprint("iiif", url_prefix="/iiif/collections")
MEDIA_TYPES = (
    f'application/ld+json;profile="{IIIF_CONTEXT}"',
    "application/ld+json",
    "application/json",
)


def iiif_error(message: str, status: int) -> response.HTTPResponse:
    return response.json({"message": message}, status=status)


async def finish_response(req, resp):
    """Routing errors have no blueprint, but still need IIIF JSON responses."""
    if req.path.split("/", 2)[1] != "iiif":
        return None

    if resp.status == 405:
        error = iiif_error("Method not allowed", 405)
        if "Allow" in resp.headers:
            error.headers["Allow"] = resp.headers["Allow"]

        return error
    return None


@iiif_blueprint.on_request
async def prepare_request(req):
    if req.method == "OPTIONS":
        return response.empty(status=204)

    if not req.path.endswith("/"):
        suffix = f"?{req.query_string}" if req.query_string else ""
        return response.redirect(f"{get_site(req)}{req.path}/{suffix}", status=308)
    req.ctx.iiif_media_type = negotiate_media_type(
        req.headers.get("Accept"), MEDIA_TYPES
    )

    if req.ctx.iiif_media_type is None:
        return iiif_error("No acceptable IIIF representation", 406)
    return None


@iiif_blueprint.exception(Exception)
async def handle_error(req, exc):
    if isinstance(exc, SolrError):
        logger.exception("Solr failure building IIIF collection")
        return iiif_error("IIIF collections are temporarily unavailable", 503)
    if isinstance(exc, SanicException):
        return iiif_error(str(exc), exc.status_code)
    logger.exception("Failure building IIIF collection")
    return iiif_error("Unable to build IIIF collection", 500)


def send_collection(req, data: dict) -> response.HTTPResponse:
    return response.json(data, content_type=req.ctx.iiif_media_type)


@iiif_blueprint.route("/", methods=["GET", "HEAD", "OPTIONS"], strict_slashes=False)
async def root(req):
    return send_collection(req, await build_root(req))


@iiif_blueprint.route(
    "/institutions/<institution_id:str>/",
    methods=["GET", "HEAD", "OPTIONS"],
    strict_slashes=False,
)
async def institution(req, institution_id: str):
    return send_collection(req, await build_institution(req, institution_id))


@iiif_blueprint.route(
    "/institutions/<institution_id:str>/<material:str>/",
    methods=["GET", "HEAD", "OPTIONS"],
    strict_slashes=False,
)
async def material_collection(req, institution_id: str, material: str):
    return send_collection(req, await build_material(req, institution_id, material))


@iiif_blueprint.route(
    "/institutions/<institution_id:str>/<material:str>/<page:str>/",
    methods=["GET", "HEAD", "OPTIONS"],
    strict_slashes=False,
)
async def subdivision(req, institution_id: str, material: str, page: str):
    return send_collection(
        req, await build_material(req, institution_id, material, page)
    )
