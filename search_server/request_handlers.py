from collections.abc import Callable

import httpx
import orjson
from sanic import request, response
from sanic.log import logger
from small_asc.client import SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.identifiers import get_identifier
from search_server.helpers.jsonld import RouteContextMap
from search_server.helpers.linked_data import to_expanded_jsonld, to_ntriples, to_turtle
from search_server.resources.tombstones import handle_tombstone
from search_server.template_render import render_template

JSONLD_MEDIA_TYPE = "application/ld+json"
JSON_MEDIA_TYPE = "application/json"
TURTLE_MEDIA_TYPE = "text/turtle"
NTRIPLES_MEDIA_TYPE = "application/n-triples"
MARCXML_MEDIA_TYPE = "application/marcxml+xml"
EXPANDED_JSONLD_MEDIA_TYPE = "application/ld+json;profile=expanded"
HTML_MEDIA_TYPE = "text/html"
ANY_MEDIA_TYPE = "*/*"


async def tombstone_or_not_found(req: request.Request) -> response.HTTPResponse:
    maybe_tombstone: dict | None = await handle_tombstone(req)
    if maybe_tombstone:
        return response.json(maybe_tombstone, status=410)

    return response.json(
        {"message": "The requested resource was not found"}, status=404
    )


def send_json_response(
    req: request.Request, serialized_results: dict, debug_response: bool
) -> response.HTTPResponse:
    accept: str | None = req.headers.get("Accept")

    # send_json_response should only be called if the only media types are
    # JSON.
    if accept:
        # In case the header has other values in it, take only the first.
        typ: list[str] = accept.split(";")
        ct = typ[0] if typ else JSONLD_MEDIA_TYPE
    else:
        # assume JSON-LD by default.
        ct = JSONLD_MEDIA_TYPE

    return response.json(
        serialized_results,
        content_type=f"{ct};charset=utf-8",
        option=orjson.OPT_INDENT_2 if debug_response else 0,
    )


async def handle_request(
    req: request.Request, handler: Callable, suppress_context: bool = False, **kwargs
) -> response.HTTPResponse:
    """
    Takes in a request object and a function for handling the request. This function should return
    a Dictionary object for the result of the request, or None if the requested object was not found.

    IDs for the objects being requested, as parsed from the path, should be sent as the keyword arguments.

    Returns a JSON response back to the user if successful, or an error if not.

    :param req: A Sanic request object
    :param handler: A function for handling the request
    :param suppress_context: Whether to suppress the @context when delivering
    :param kwargs: A set of options to be passed to the
    :return: A JSON Response, or an error if not successful.
    """
    accept: str | None = req.headers.get("Accept")
    app_context = req.app.ctx

    # assume success unless otherwise
    response_code: int = 200
    data_obj: dict | None

    try:
        data_obj = await handler(req, **kwargs)
    except SolrError as err:
        data_obj = {"message": f"Error sending search to Solr. {err}"}
        response_code = 500

    # This will return a 404 for both the cases where the response is None, and where
    # it is an empty dictionary.
    if not data_obj:
        data_obj = await handle_tombstone(req)
        if data_obj:
            response_code = 410
        else:
            data_obj = {"message": "The requested resource was not found"}
            response_code = 404

    if accept and (HTML_MEDIA_TYPE in accept):
        # If we have an HTML request, then this will serve the template with the
        # appropriate status code. Anything beyond this point is an API request.
        rendered_template: str = render_template(app_context, req, data_obj)
        return response.html(rendered_template, status=response_code)

    # Anything past this point is a data API response.
    if response_code in (410, 404, 500):
        return response.json(data_obj, status=response_code)

    # Add the appropriate context to the result dictionary
    if req.route and req.route.name in RouteContextMap:
        ctx_options = RouteContextMap[req.route.name]
    else:
        ctx_options = RouteContextMap["__default"]

    res: dict
    if accept and TURTLE_MEDIA_TYPE in accept:
        # Always embed the context for turtle, as it avoids a lookup via the URI
        ctx_val = {"@context": ctx_options.context}
        res = {**ctx_val, **data_obj}
        ttl = to_turtle(res)
        return response.text(ttl, content_type=TURTLE_MEDIA_TYPE)

    if accept and NTRIPLES_MEDIA_TYPE in accept:
        ctx_val = {"@context": ctx_options.context}
        res = {**ctx_val, **data_obj}
        nt: str = to_ntriples(res)
        return response.text(nt, content_type=NTRIPLES_MEDIA_TYPE)

    if accept and MARCXML_MEDIA_TYPE in accept:
        if sid := req.match_info.get("source_id"):
            rtype = "sources"
            rid = sid
        elif iid := req.match_info.get("institution_id"):
            rtype = "institutions"
            rid = iid
        elif pid := req.match_info.get("person_id"):
            rtype = "people"
            rid = pid
        elif pid := req.match_info.get("work_id"):
            rtype = "works"
            rid = pid
        else:
            return response.json(
                {"message": "Cannot retrieve MARCXML for this resource."}, status=406
            )

        auth_headers: dict = {
            "Authorization": f"Token {app_context.config['common']['muscat_auth']}"
        }

        async with httpx.AsyncClient(headers=auth_headers) as client:
            muscat_req = await client.get(
                f"https://muscat.rism.info/data/{rtype}/{rid}"
            )
            muscat_resp = muscat_req.text
            if muscat_req.status_code != 200:
                return response.json(
                    {"message": "Could not retrieve MARCXML from upstream"}, status=500
                )

        return response.text(muscat_resp, content_type=MARCXML_MEDIA_TYPE)

    if accept and ";profile=expanded" in accept:
        ctx_val = {"@context": ctx_options.context}
        res = {**ctx_val, **data_obj}
        exp = to_expanded_jsonld(res)
        # The response is already encoded as a string, so we just send it as text
        # with the appropriate content-type.
        return response.text(exp, content_type=EXPANDED_JSONLD_MEDIA_TYPE)

    logger.debug("Sending JSON")

    # We can control the embedding of the context either globally, in the configuration, or
    # per-request, with the X-Embed-Context header.
    if suppress_context:
        ctx_val = {}
    elif app_context.context_uri and "X-Embed-Context" not in req.headers:
        ctx_val = {"@context": get_identifier(req, ctx_options.route)}
    else:
        ctx_val = {"@context": ctx_options.context}

    res = {**ctx_val, **data_obj}

    return send_json_response(req, res, app_context.config["common"]["debug"])


async def handle_search(
    req: request.Request, handler: Callable, **kwargs
) -> response.HTTPResponse:
    # accept: Optional[str] = req.headers.get("Accept")

    # Check whether we can respond with the correct content type. Note that
    # this server does not handle HTML responses; these are handled before
    # the request reaches this server.
    # if accept and (("application/ld+json" not in accept) or ("application/json" not in accept)):
    #     return response.text("Supported content types for search interfaces are 'application/json' and
    #     application/ld+json'", status=406)

    accept: str | None = req.headers.get("Accept")
    if accept and (
        JSON_MEDIA_TYPE not in accept
        and JSONLD_MEDIA_TYPE not in accept
        and HTML_MEDIA_TYPE not in accept
        and ANY_MEDIA_TYPE not in accept
    ):
        status_msg = f"""Accept header {accept} is not available for this resource."""
        return response.json({"message": status_msg}, status=406)

    app_context = req.app.ctx

    try:
        data_obj: dict = await handler(req, **kwargs)
    except InvalidQueryException as e:
        return response.json({"message": f"Invalid search query. {e}"}, status=400)
    except SolrError as e:
        error_message: str = f"Error sending search to Solr. {e}"
        return response.json({"message": error_message}, status=500)

    if accept and "json" in accept:
        if not data_obj:
            return response.json(
                {"message": "The requested resource was not found"}, status=404
            )

        return send_json_response(req, data_obj, app_context.config["common"]["debug"])
    else:
        rendered_template: str = render_template(app_context, req, data_obj)
        return response.html(rendered_template)
