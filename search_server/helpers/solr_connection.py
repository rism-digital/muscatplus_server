"""
    A Singleton for a global Solr connection. Methods that wish
    to make use of a global Solr connection can import this module
    and it will give them an instance of a Solr connection that
    they can then use to perform searches.

      >>> from search_server.helpers.solr_connection import SolrConnection
      >>> res = SolrConnection.search("Some Query")

"""
from typing import Dict, Iterator, NewType, Optional
import yaml
import logging


from small_asc.client import Solr, Results

log = logging.getLogger(__name__)

config: Dict = yaml.safe_load(open('configuration.yml', 'r'))

solr_url = config['solr']['server']

SolrConnection: Solr = Solr(solr_url)

log.debug('Solr connection set to %s', solr_url)

SolrResult = NewType('SolrResult', Dict)


def result_count(**kwargs) -> int:
    """
    Takes a Solr query and returns the number of results, but does not actually retrieve them.

    :param kwargs: Keyword arguments to pass to the Solr query
    :return: The number of hits
    """
    res = SolrConnection.search({"query": "*:*", "limit": 0, "params": {**kwargs}})
    return res.hits
