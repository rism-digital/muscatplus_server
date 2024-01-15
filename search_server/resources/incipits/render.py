from typing import Optional

import orjson
from sanic import response

from search_server.helpers.vrv import create_pae_from_request, render_pae, validate_pae


async def handle_incipit_render(req) -> response.HTTPResponse:
    """ Takes an incoming string and runs it through Verovio to render as notation. Requests use the `?n=` query
        parameter as required notation input.

        Other optional parameters that may be used include:
         - ic: clef (default: G-2)
         - it: time signature (default: 4/4)
         - ik: key signature (default: no sharps, no flats -- key of C major)

        (This is the same as the request parameters for the incipit search)

        Returns SVG in the body of the response
    """
    pae: str = create_pae_from_request(req)

    # Generate random IDs to avoid ID collisions on the page.
    rendered_pae: Optional[tuple] = render_pae(pae, use_crc=False, enlarged=False)
    if not rendered_pae:
        return response.text(
            "There was a problem rendering the Plaine and Easie notation",
            status=500
        )

    svg, _ = rendered_pae
    response_headers = {'Content-Type':  "image/svg+xml;charset=utf8"}

    return response.text(svg, headers=response_headers
    )


async def handle_incipit_validate(req) -> response.HTTPResponse:
    response_headers: dict = {
        "Content-Type": "application/json; charset=utf-8"
    }
    data_obj: dict = validate_pae(req)

    return response.json(
        data_obj,
        headers=response_headers,
        option=orjson.OPT_INDENT_2 if req.app.ctx.config['common']['debug'] else 0
    )
