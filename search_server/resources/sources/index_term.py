from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.helpers.solr_connection import SolrResult


class IndexTermsList(JSONLDContextDictSerializer):
    pass

    def items(self, obj: SolrResult):
        pass