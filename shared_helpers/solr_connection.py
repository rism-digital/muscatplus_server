"""
    A Singleton for a global Solr connection. Methods that wish
    to make use of a global Solr connection can import this module
    and it will give them an instance of a Solr connection that
    they can then use to perform searches.

      >>> from shared_helpers.solr_connection import SolrConnection
      >>> res = SolrConnection.search({"query": "Some query"})

"""
import logging
from typing import NewType, Optional

import yaml
from small_asc.client import Solr, Results

log = logging.getLogger("mp_server")

config: dict = yaml.safe_load(open('configuration.yml', 'r'))

solr_url = config['solr']['server']

SolrConnection: Solr = Solr(solr_url)

log.debug('Solr connection set to %s', solr_url)

SolrResult = NewType('SolrResult', dict)


async def execute_query(solr_params: dict) -> Results:
    """
    Executes a search query. Expects a pre-compiled dictionary of parameters to pass to Solr. Raises SolrError
    if there was a problem with the query.

    :param solr_params: A dictionary representing a JSON Search API query for Solr.
    :return: A Solr Results object with the results of a query.
    """
    solr_res: Results = await SolrConnection.search(solr_params)
    return solr_res


async def result_count(**kwargs) -> int:
    """
    Takes a Solr query and returns the number of results, but does not actually retrieve them.

    :param kwargs: Keyword arguments to pass to the Solr query
    :return: The number of hits
    """
    res: Results = await SolrConnection.search({"query": "*:*", "limit": 0, "params": {**kwargs}})
    return res.hits


async def is_composite(source_id: str) -> bool:
    res: Optional[dict] = await SolrConnection.get(source_id, ["record_type_s"])
    return res["record_type_s"] == "composite" if res and "record_type_s" in res else False
