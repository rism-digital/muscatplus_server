import logging

import ypres
from small_asc.client import Results

from search_server.helpers.solr_connection import SolrConnection
from search_server.resources.search.base_search import BaseSearchResults
from search_server.resources.search.incipit_result import IncipitSearchResult
from search_server.resources.search.institution_result import InstitutionSearchResult
from search_server.resources.search.person_result import PersonSearchResult
from search_server.resources.search.source_result import SourceSearchResult

log = logging.getLogger("mp_server")


class SearchResults(BaseSearchResults):
    query_validation = ypres.MethodField(label="queryValidation")

    def get_query_validation(self, obj: Results) -> dict | None:
        if "query_validation" not in self.context:
            return None

        return self.context["query_validation"]

    def get_modes(self, obj: Results) -> dict | None:
        is_probe: bool = self.context.get("probe_request", False)
        if is_probe:
            return None

        facet_results: dict | None = obj.raw_response.get("facets")
        if not facet_results:
            return None

        mode_facet: dict | None = facet_results.get("mode")
        # if, for some reason, we don't have a mode facet we return gracefully.
        if not mode_facet:
            return None

        mode_buckets: list = mode_facet.get("buckets", [])
        # if there are no buckets for this mode, then we shouldn't return the
        # mode facet block at all.
        if len(mode_buckets) == 0:
            return None

        req = self.context["request"]
        cfg: dict = req.app.ctx.config
        transl: dict = req.app.ctx.translations

        mode_items: list = []
        mode_config: dict = cfg["search"]["modes"]
        # Put the returned modes into a dictionary so we can look up the buckets by the key. The format is
        # {type: count}, where 'type' is the value from the Solr type field, and 'count' is the number of
        # records returned.
        mode_results: dict = {f"{mode['val']}": mode["count"] for mode in mode_buckets}

        # This will ensure the modes are returned in the order they're listed in the configuration file. Otherwise
        #  they are returned by the order of results.
        for mode, config in mode_config.items():
            record_type = config["record_type"]
            if record_type not in mode_results:
                continue

            translation_key: str = config["label"]

            mode_items.append(
                {
                    "value": mode,
                    "label": transl.get(translation_key),
                    "count": mode_results[record_type],
                }
            )

        return {
            "alias": "mode",
            "label": {"none": ["Result type"]},  # TODO: Translate!
            "type": "rism:ModeFacet",
            "items": mode_items,
        }

    async def get_items(self, obj: Results) -> list | None:
        is_probe: bool = self.context.get("probe_request", False)
        # If we have no hits, or we have a 'probe' request, then don't
        # return an empty items block.
        if obj.hits == 0 or is_probe:
            return None

        results: list[dict] = []
        req = self.context["request"]
        is_composite: bool = self.context.get("is_composite", False)

        for d in obj.docs:
            dtype: str = d["type"]

            match dtype:
                case "source":
                    results.append(
                        SourceSearchResult(d, context={"request": req}).serialized
                    )
                case "person":
                    results.append(
                        PersonSearchResult(d, context={"request": req}).serialized
                    )
                case "institution":
                    results.append(
                        InstitutionSearchResult(d, context={"request": req}).serialized
                    )
                case "incipit":
                    results.append(
                        IncipitSearchResult(
                            d,
                            context={
                                "request": req,
                                "query_pae_features": self.context.get(
                                    "query_pae_features"
                                ),
                            },
                        ).serialized
                    )
                case "holding" if is_composite is True:
                    # The SLOW path, but there shouldn't be many of these, so hopefully it won't be too bad.
                    # Look up the source based on the ID from the holding, then fetch the doc. This means this will
                    # trigger a Solr lookup for every result in the list that is a holding, but this should only ever
                    # happen when a source is marked as composite, and the relationship to an item in the source is
                    # a holding record.
                    source_id: str = d["source_id"]
                    source_doc: dict | None = await SolrConnection.get(source_id)  # type: ignore
                    if not source_doc:
                        log.error("Malformed holding %s", d["id"])
                        continue

                    results.append(
                        SourceSearchResult(
                            source_doc, context={"request": req}
                        ).serialized
                    )
                case _:
                    continue

        return results
