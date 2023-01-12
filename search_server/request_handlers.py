import logging
from typing import Callable, Optional

from sanic import request, response
from small_asc.client import SolrError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.linked_data import to_turtle, to_expanded_jsonld

log = logging.getLogger("mp_server")


def send_json_response(serialized_results: dict, debug_response: bool) -> response.HTTPResponse:
    response_headers: dict = {
        "Content-Type": "application/ld+json; charset=utf-8"
    }

    return response.json(
        serialized_results,
        headers=response_headers,
        # escape_forward_slashes=False,
        # indent=(4 if debug_response else 0)
    )


async def handle_request(req: request.Request, handler: Callable, **kwargs) -> response.HTTPResponse:
    """
    Takes in a request object and a function for handling the request. This function should return
    a Dictionary object for the result of the request, or None if the requested object was not found.

    IDs for the objects being requested, as parsed from the path, should be sent as the keyword arguments.

    Returns a JSON response back to the user if successful, or an error if not.

    :param req: A Sanic request object
    :param handler: A function for handling the request
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

    response_headers: dict = {}

    if accept and "text/turtle" in accept:
        # return response.text("Turtle responses will be implemented in the future.", status=501)
        ttl = to_turtle(data_obj)
        return response.text(ttl, headers={"Content-Type": "text/turtle"})
    elif accept and "application/n-quads" in accept:
        return response.text("N-Quad responses will be implemented in the future", status=501)
    elif accept and ";profile=expanded" in accept:
        exp = to_expanded_jsonld(data_obj)
        return response.text(exp, headers={"Content-Type": "application/ld+json;profile=expanded"})
    else:
        log.debug("Sending JSON-LD")
        # The default return type is JSON-LD
        return send_json_response(data_obj, req.app.ctx.config['common']['debug'])


async def handle_search(req: request.Request, handler: Callable, **kwargs) -> response.HTTPResponse:
    # accept: Optional[str] = req.headers.get("Accept")

    # Check whether we can respond with the correct content type. Note that
    # this server does not handle HTML responses; these are handled before
    # the request reaches this server.
    # if accept and (("application/ld+json" not in accept) or ("application/json" not in accept)):
    #     return response.text("Supported content types for search interfaces are 'application/json' and
    #     application/ld+json'", status=406)

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

    return send_json_response(data_obj, req.app.ctx.config['common']['debug'])
