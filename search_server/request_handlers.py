import logging
from typing import Callable, Optional

import orjson.orjson
from sanic import request, response
from small_asc.client import SolrError

from shared_helpers.identifiers import get_identifier
from shared_helpers.jsonld import RouteContextMap
from search_server.exceptions import InvalidQueryException
from search_server.helpers.linked_data import to_turtle, to_expanded_jsonld, to_ntriples

log = logging.getLogger("mp_server")


async def send_json_response(serialized_results: dict, debug_response: bool) -> response.HTTPResponse:
    response_headers: dict = {
        "Content-Type": "application/ld+json; charset=utf-8"
    }

    return response.json(
        serialized_results,
        headers=response_headers,
        option=orjson.OPT_INDENT_2 if debug_response else 0
    )


async def handle_request(req: request.Request,
                         handler: Callable,
                         suppress_context: bool = False,
                         **kwargs) -> response.HTTPResponse:
    """
    Takes in a request object and a function for handling the request. This function should return
    a Dictionary object for the result of the request, or None if the requested object was not found.

    IDs for the objects being requested, as parsed from the path, should be sent as the keyword arguments.

    Returns a JSON response back to the user if successful, or an error if not.

    :param req: A Sanic request object
    :param handler: A function for handling the request
    :param suppress_context: Whether or not to suppress the @context when delivering
    :param kwargs: A set of options to be passed to the
    :return: A JSON Response, or an error if not successful.
    """
    accept: Optional[str] = req.headers.get("Accept")

    data_obj: Optional[dict] = await handler(req, **kwargs)

    # This will return a 404 for both the cases where the response is None, and where
    # it is an empty dictionary.
    if not data_obj:
        return response.text(
            "The requested resource was not found",
            status=404
        )

    # Add the appropriate context to the result dictionary
    if req.route.name in RouteContextMap:
        ctx_options = RouteContextMap[req.route.name]
    else:
        ctx_options = RouteContextMap["__default"]

    if accept and "text/turtle" in accept:
        # Always embed the context for turtle, as it avoids a lookup via the URI
        ctx_val = {"@context": ctx_options.context}
        res: dict = {**ctx_val, **data_obj}
        ttl = to_turtle(res)
        return response.text(ttl, headers={"Content-Type": "text/turtle"})
    elif accept and "application/n-triples" in accept:
        ctx_val = {"@context": ctx_options.context}
        res: dict = {**ctx_val, **data_obj}
        nt: str = to_ntriples(res)
        return response.text(nt, headers={"Content-Type": "application/n-triples"})
    elif accept and ";profile=expanded" in accept:
        ctx_val = {"@context": ctx_options.context}
        res: dict = {**ctx_val, **data_obj}
        exp = to_expanded_jsonld(res)
        return response.text(exp, headers={"Content-Type": "application/ld+json;profile=expanded"})
    else:
        log.debug("Sending JSON-LD")

        # We can control the embedding of the context either globally, in the configuration, or
        # per-request, with the X-Embed-Context header.
        if suppress_context:
            ctx_val = {}
        elif req.app.ctx.context_uri and "X-Embed-Context" not in req.headers:
            ctx_val = {"@context": get_identifier(req, ctx_options.route)}
        else:
            ctx_val = {"@context": ctx_options.context}

        res: dict = {**ctx_val, **data_obj}

        return await send_json_response(res, req.app.ctx.config['common']['debug'])


async def handle_search(req: request.Request, handler: Callable, **kwargs) -> response.HTTPResponse:
    # accept: Optional[str] = req.headers.get("Accept")

    # Check whether we can respond with the correct content type. Note that
    # this server does not handle HTML responses; these are handled before
    # the request reaches this server.
    # if accept and (("application/ld+json" not in accept) or ("application/json" not in accept)):
    #     return response.text("Supported content types for search interfaces are 'application/json' and
    #     application/ld+json'", status=406)

    accept: Optional[str] = req.headers.get("Accept")
    if accept and "application/ld+json" not in accept:
        status_msg = f"""Accept header {accept} is not available for this resource. 
        Only application/ld+json is available"""
        return response.text(status_msg, status=406)

    try:
        data_obj: dict = await handler(req, **kwargs)
    except InvalidQueryException as e:
        return response.text(f"Invalid search query. {e}", status=400)
    except SolrError as e:
        error_message: str = f"Error sending search to Solr. {e}"
        return response.text(error_message, status=500)

    if not data_obj:
        return response.text("The requested resource was not found",
                             status=404)

    return await send_json_response(data_obj, req.app.ctx.config['common']['debug'])
