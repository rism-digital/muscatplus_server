import logging
from typing import Dict, List, Optional

from small_asc.client import Results

from search_server.resources.search.base_search import BaseSearchResults
from search_server.resources.search.search_results import SourceSearchResult

log = logging.getLogger(__name__)


class InstitutionResults(BaseSearchResults):
    def get_modes(self, obj: Results) -> Optional[Dict]:
        return None

    def get_items(self, obj: Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        return SourceSearchResult(obj.docs,
                                  many=True,
                                  context={"request": self.context.get("request")}).data
