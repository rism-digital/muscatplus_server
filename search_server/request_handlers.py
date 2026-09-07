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


def accepts(accept: str | None, media_type: str) -> bool:
    """Match complete media types, ignoring quality values; HTML takes priority.

    Missing, wildcard and unrecognized headers default to HTML. Parameters
    are ignored unless explicitly requested (as for expanded JSON-LD).
    """
    entries = [entry.strip().split(";") for entry in (accept or "").split(",")]
    types = {entry[0].strip().lower() for entry in entries}
    supported = {
        JSON_MEDIA_TYPE,
        JSONLD_MEDIA_TYPE,
        TURTLE_MEDIA_TYPE,
        NTRIPLES_MEDIA_TYPE,
        MARCXML_MEDIA_TYPE,
    }
    html = HTML_MEDIA_TYPE in types or ANY_MEDIA_TYPE in types or not types & supported
    if media_type == HTML_MEDIA_TYPE:
        return html
    if html:
        return False
    base, _, parameter = media_type.partition(";")
    return any(
        entry[0].strip().lower() == base
        and (not parameter or parameter in [part.strip() for part in entry[1:]])
        for entry in entries
    )


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
    req: request.Request,
    handler: Callable,
    suppress_context: bool = False,
    raw_json_response: bool = False,
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
            data_obj = {
                "id": "",
                "message": "The requested resource was not found",
                "type": "rism:NotFound",
            }
            response_code = 404

    # If we have an HTML request, then this will serve the template with the
    # appropriate status code. Anything beyond this point is an API request.
    # If the handler sets a raw JSON response, then bypass whatever Accept values
    # they requested. This means bypassing the HTML rendering.
    if accepts(accept, HTML_MEDIA_TYPE) and not raw_json_response:
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
    if accepts(accept, TURTLE_MEDIA_TYPE):
        # Always embed the context for turtle, as it avoids a lookup via the URI
        ctx_val = {"@context": ctx_options.context}
        res = {**ctx_val, **data_obj}
        ttl = to_turtle(res)
        return response.text(ttl, content_type=TURTLE_MEDIA_TYPE)

    if accepts(accept, NTRIPLES_MEDIA_TYPE):
        ctx_val = {"@context": ctx_options.context}
        res = {**ctx_val, **data_obj}
        nt: str = to_ntriples(res)
        return response.text(nt, content_type=NTRIPLES_MEDIA_TYPE)

    if accepts(accept, MARCXML_MEDIA_TYPE):
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

    if accepts(accept, EXPANDED_JSONLD_MEDIA_TYPE):
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
    accept: str | None = req.headers.get("Accept")
    app_context = req.app.ctx

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

    if accepts(accept, JSON_MEDIA_TYPE) or accepts(accept, JSONLD_MEDIA_TYPE):
        if not data_obj:
            return response.json(
                {"message": "The requested resource was not found"}, status=404
            )

        return send_json_response(
            req,
            with_included_type_nodes(
                data_obj, ignored_keys=null_context_terms(ctx_options.context)
            ),
            app_context.config["common"]["debug"],
        )
    else:
        rendered_template: str = render_template(app_context, req, data_obj)
        return response.html(rendered_template)
