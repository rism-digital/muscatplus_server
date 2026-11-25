from collections.abc import Callable

import orjson
from pyreqwest.client import ClientBuilder
from sanic import request, response
from sanic.log import logger
from small_asc.client import SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.identifiers import get_identifier
from search_server.helpers.jsonld import (
    RouteContextMap,
    null_context_terms,
    with_included_type_nodes,
)
from search_server.helpers.linked_data import to_expanded_jsonld, to_ntriples, to_turtle
from search_server.negotiation import negotiate_media_type
from search_server.resources.tombstones import handle_tombstone
from search_server.template_render import render_template

JSONLD_MEDIA_TYPE = "application/ld+json"
JSON_MEDIA_TYPE = "application/json"
TURTLE_MEDIA_TYPE = "text/turtle"
NTRIPLES_MEDIA_TYPE = "application/n-triples"
MARCXML_MEDIA_TYPE = "application/marcxml+xml"
EXPANDED_JSONLD_MEDIA_TYPE = "application/ld+json;profile=expanded"
HTML_MEDIA_TYPE = "text/html"
MEI_MEDIA_TYPE = "application/mei+xml"
PNG_MEDIA_TYPE = "image/png"

PUBLIC_PAGE_MEDIA_TYPES = (HTML_MEDIA_TYPE, JSONLD_MEDIA_TYPE, JSON_MEDIA_TYPE)
RECORD_MEDIA_TYPES = (
    HTML_MEDIA_TYPE,
    TURTLE_MEDIA_TYPE,
    NTRIPLES_MEDIA_TYPE,
    MARCXML_MEDIA_TYPE,
    JSONLD_MEDIA_TYPE,
    EXPANDED_JSONLD_MEDIA_TYPE,
    JSON_MEDIA_TYPE,
)


def public_not_found_response(
    req: request.Request, data: dict, media_type: str | None
) -> response.HTTPResponse:
    headers = {"Vary": "Accept", "Cache-Control": "no-store"}
    if media_type == HTML_MEDIA_TYPE:
        return response.html(
            render_template(req.app.ctx, req, None), status=404, headers=headers
        )
    if media_type is None:
        return response.empty(status=404, headers=headers)
    # Keep the existing JSON error contract, including for JSON-LD clients.
    return response.json(data, status=404, headers=headers)


async def tombstone_or_not_found(req: request.Request) -> response.HTTPResponse:
    maybe_tombstone: dict | None = await handle_tombstone(req)
    if maybe_tombstone:
        return response.json(maybe_tombstone, status=410)

    return response.json(
        {"message": "The requested resource was not found"}, status=404
    )


def send_json_response(
    req: request.Request,
    serialized_results: dict,
    debug_response: bool,
    media_type: str | None = None,
) -> response.HTTPResponse:
    selected_media_type = media_type or negotiate_media_type(
        req.headers.get("Accept"), [JSONLD_MEDIA_TYPE, JSON_MEDIA_TYPE]
    )
    if selected_media_type is None:
        selected_media_type = JSONLD_MEDIA_TYPE
    ct = f"{selected_media_type};charset=utf-8"

    return response.json(
        serialized_results,
        content_type=ct,
        option=orjson.OPT_INDENT_2 if debug_response else 0,
    )


async def handle_request(
    req: request.Request,
    handler: Callable,
    suppress_context: bool = False,
    raw_json_response: bool = False,
    *,
    selected_media_type: str | None = None,
    **kwargs,
) -> response.HTTPResponse:
    """
    Takes in a request object and a function for handling the request. This function should return
    a Dictionary object for the result of the request, or None if the requested object was not found.

    IDs for the objects being requested, as parsed from the path, should be sent as the keyword arguments.

    Returns a JSON response back to the user if successful, or an error if not.

    :param req: A Sanic request object
    :param handler: A function for handling the request
    :param suppress_context: Whether to suppress the @context when delivering
    :param raw_json_response: Treat the serialized object as a raw response, bypassing JSON-LD and Template processes
    :param selected_media_type: Reuse a representation already negotiated by the route.
    :param kwargs: A set of options to be passed to the
    :return: A JSON Response, or an error if not successful.
    """
    app_context = req.app.ctx
    if not raw_json_response and selected_media_type is None:
        selected_media_type = negotiate_media_type(
            req.headers.get("Accept"), RECORD_MEDIA_TYPES
        )
        if selected_media_type is None:
            return response.empty(status=406)

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
            data_obj = {
                "id": "",
                "message": "The requested resource was not found",
                "type": "rism:NotFound",
            }
            response_code = 404

    if response_code == 404 and not raw_json_response:
        return public_not_found_response(req, data_obj, selected_media_type)

    # If we have an HTML request, then this will serve the template with the
    # appropriate status code. Anything beyond this point is an API request.
    # If the handler sets a raw JSON response, then bypass whatever Accept values
    # they requested. This means bypassing the HTML rendering.
    if selected_media_type == HTML_MEDIA_TYPE and not raw_json_response:
        rendered_template: str = render_template(app_context, req, data_obj)
        return response.html(rendered_template, status=response_code)

    # Anything past this point is a data API response. If we have set
    # a non-200 response code, ship it out here.
    if response_code in (410, 404, 500):
        return response.json(data_obj, status=response_code)

    # We can bypass all the JSON-LD stuff and return early if we have
    # the raw JSON response set.
    if raw_json_response:
        return response.json(
            data_obj,
            option=orjson.OPT_INDENT_2 if app_context.config["common"]["debug"] else 0,
        )

    # Add the appropriate context to the result dictionary
    if req.route and req.route.name in RouteContextMap:
        ctx_options = RouteContextMap[req.route.name]
    else:
        ctx_options = RouteContextMap["__default"]

    data_obj = with_included_type_nodes(
        data_obj, ignored_keys=null_context_terms(ctx_options.context)
    )

    res: dict
    if selected_media_type == TURTLE_MEDIA_TYPE:
        # Always embed the context for turtle, as it avoids a lookup via the URI
        ctx_val = {"@context": ctx_options.context}
        res = {**ctx_val, **data_obj}
        ttl = to_turtle(res)
        return response.text(ttl, content_type=TURTLE_MEDIA_TYPE)

    if selected_media_type == NTRIPLES_MEDIA_TYPE:
        ctx_val = {"@context": ctx_options.context}
        res = {**ctx_val, **data_obj}
        nt: str = to_ntriples(res)
        return response.text(nt, content_type=NTRIPLES_MEDIA_TYPE)

    if selected_media_type == MARCXML_MEDIA_TYPE:
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

        async with ClientBuilder().default_headers(auth_headers).build() as client:
            muscat_req = await client.get(
                f"https://muscat.rism.info/data/{rtype}/{rid}"
            ).build().send()
            if muscat_req.status != 200:
                return response.json(
                    {"message": "Could not retrieve MARCXML from upstream"}, status=500
                )
            muscat_resp = await muscat_req.text()

        return response.text(muscat_resp, content_type=MARCXML_MEDIA_TYPE)

    if selected_media_type == EXPANDED_JSONLD_MEDIA_TYPE:
        ctx_val = {"@context": ctx_options.context}
        res = {**ctx_val, **data_obj}
        exp = to_expanded_jsonld(res)
        # The response is already encoded as a string, so we just send it as text
        # with the appropriate content-type.
        return response.text(exp, content_type=EXPANDED_JSONLD_MEDIA_TYPE)

    logger.debug("Sending JSON")

    # We can control the embedding of the context either globally, in the configuration, or
    # per-request, with the X-Embed-Context header.
    varies_by_embed_context = not suppress_context and app_context.context_uri
    if suppress_context:
        ctx_val = {}
    elif varies_by_embed_context and not req.headers.get("X-Embed-Context"):
        ctx_val = {"@context": get_identifier(req, ctx_options.route)}
    else:
        ctx_val = {"@context": ctx_options.context}

    res = {**ctx_val, **data_obj}

    resp = send_json_response(
        req,
        res,
        app_context.config["common"]["debug"],
        media_type=selected_media_type,
    )
    if varies_by_embed_context:
        resp.headers.add("Vary", "X-Embed-Context")
    return resp


async def handle_search(
    req: request.Request, handler: Callable, **kwargs
) -> response.HTTPResponse:
    accept: str | None = req.headers.get("Accept")
    app_context = req.app.ctx
    selected_media_type = negotiate_media_type(accept, PUBLIC_PAGE_MEDIA_TYPES)
    if selected_media_type is None:
        return response.empty(status=406)

    if req.route and req.route.name in RouteContextMap:
        ctx_options = RouteContextMap[req.route.name]
    else:
        ctx_options = RouteContextMap["__default"]

    try:
        data_obj: dict = await handler(req, **kwargs)
    except InvalidQueryException as e:
        return response.json({"message": f"Invalid search query. {e}"}, status=400)
    except SolrError as e:
        error_message: str = f"Error sending search to Solr. {e}"
        return response.json({"message": error_message}, status=500)

    if not data_obj:
        return public_not_found_response(
            req, {"message": "The requested resource was not found"}, selected_media_type
        )

    if selected_media_type != HTML_MEDIA_TYPE:
        return send_json_response(
            req,
            with_included_type_nodes(
                data_obj, ignored_keys=null_context_terms(ctx_options.context)
            ),
            app_context.config["common"]["debug"],
            media_type=selected_media_type,
        )
    else:
        rendered_template: str = render_template(app_context, req, data_obj)
        return response.html(rendered_template)
