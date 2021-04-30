import logging
from typing import Callable, Optional, Dict

import pysolr
from sanic import request, response

from search_server.exceptions import InvalidQueryException
from search_server.helpers.semantic_web import to_turtle, to_rdf

log = logging.getLogger("mp_server")


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

    data_obj: Optional[Dict] = handler(req, **kwargs)

    if not data_obj:
        return response.text(
            "The requested resource was not found",
            status=404
        )

    response_headers: Dict = {}

    if accept and "text/turtle" in accept:
        log.debug("Sending Turtle")

        turtle_resp: str = to_turtle(data_obj)
        response_headers["Content-Type"] = "text/turtle; charset=utf-8"

        return response.text(
            turtle_resp,
            headers=response_headers
        )
    elif accept and "application/n-quads" in accept:
        log.debug("Sending RDF")
        rdf_resp: str = to_rdf(data_obj)
        response_headers["Content-Type"] = "application/n-quads; charset=utf-8"

        return response.text(
            rdf_resp,
            headers=response_headers
        )
    else:
        log.debug("Sending JSON-LD")
        # The default return type is JSON-LD
        response_headers["Content-Type"] = "application/ld+json; charset=utf-8"

        return response.json(
            data_obj,
            headers=response_headers,
            escape_forward_slashes=False,
            indent=(4 if req.app.ctx.config['common']['debug'] else 0)
        )


async def handle_search_request(req: request.Request, handler: Callable, **kwargs) -> response.HTTPResponse:
    accept: Optional[str] = req.headers.get("Accept")

    # Check whether we can respond with the correct content type. Note that
    # this server does not handle HTML responses; these are handled before
    # the request reaches this server.
    # if accept and (("application/ld+json" not in accept) or ("application/json" not in accept)):
    #     return response.text("Supported content types for search interfaces are 'application/json' and application/ld+json'",
    #                          status=406)

    try:
        data_obj: Dict = handler(req, **kwargs)
    except InvalidQueryException as e:
        return response.text(f"Invalid search query. {e}", status=400)
    except pysolr.SolrError as e:
        error_message: str = f"Error sending search to Solr. {e}"
        log.exception(error_message)
        return response.text(error_message, status=500)

    if not data_obj:
        return response.text("The requested resource was not found",
                             status=404)

    response_headers: Dict = {
        "Content-Type": "application/ld+json; charset=utf-8"
    }

    return response.json(
        data_obj,
        headers=response_headers,
        escape_forward_slashes=False,
        indent=(4 if req.app.config['common']['debug'] else 0)
    )