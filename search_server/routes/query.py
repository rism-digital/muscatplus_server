from sanic import Blueprint

from search_server.request_handlers import handle_search
from search_server.resources.search.probe import handle_probe_request
from search_server.resources.search.search import handle_search_request
from search_server.resources.suggest.suggest import handle_suggest_request

query_blueprint: Blueprint = Blueprint("query")


# The main search interface request handler.
@query_blueprint.route("/search/")
async def search(req):
    """
    For querying, the following query parameters are recognized:

     - `q`: The main query parameter. Required, Non-repeatable! "*:*" if not explicitly passed in.
     - `nc`: The requested national collection filter. This applies to anything that is limited nationally, such
             as sources and institutions. When a `nc` filter is applied, things *not* limited nationally, such as
             people, are omitted from the response.
     - `fq`: The main filter queries. Repeatable. Takes parameters like "name:Smith, John" and uses them as facet
             queries.
     - `fb`: The filter behaviours. Repeatable. Adjusts the named filter behaviour from 'intersection' and 'union'. For
             example, if we have `fq=composer:Smith, John&fq=composer:Smythe, Jane`, then `&fb=composer:union` would
             change the behaviour of the `composer` facet. Acceptable values are `intersection` (default) and `union`.
     - `mode`: Sets the mode of the search to return records of only that type.
     - `page`: Controls the return of the result page. Pages can be of multiple size, but this should always skip to the
               correct page.
     - `rows`: Number of results per page.
     - `sort`: Controls the sorting of returned results

    Some parameters are specific to only incipit searches:

     - `n`: A Plaine and Easie string containing an encoded incipit search.
     - `im`: Incipit search mode. Controls the type of mode used for matching incipits. Supports a value of 'intervals'
            (default) and "exact-pitches".
     - `ic`: Controls the *rendering* of the incipit clef.
     - `it`: Controls the *rendering* of the incipit time signature.
     - `ik`: Controls the incipit key signature. The value of this will
             also change interval values, so it may have an impact on the results.
    """
    return await handle_search(req, handle_search_request)


# The Suggest request is available on specific fields (configured as query fields).
# This uses the Solr TermComponent interface to suggest terms for use in an autocomplete
# lookup.
@query_blueprint.route("/suggest/")
async def suggest(req):
    """
    Handles suggest requests for specifically-configured fields. The supported query parameters are:

    - `alias`: The field name to search for term suggestions
    - `q`: The query term for which a suggestion is to be made
    """
    return await handle_suggest_request(req)


@query_blueprint.route("/probe/")
async def probe(req):
    """
    A probe request will perform a search, so it has all the functionality
    of the [/search](#search) handler. The difference is that it will not return any
    actual results. Instead, it will return the total number of results, and any facets or
    modes that would be active for a given search query.
    """
    return await handle_search(req, handle_probe_request)
