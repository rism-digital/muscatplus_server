from __future__ import annotations

from types import SimpleNamespace

import pytest
from small_asc.query import EmptyFieldQueryError, FieldNotFoundError, QueryParseError

from search_server.exceptions import InvalidQueryException
from search_server.helpers.search_request import (
    DEFAULT_QUERY_STRING,
    FacetBehaviourValues,
    SearchRequest,
    _create_parameter_facet,
    _create_range_facet,
    _create_select_facet,
    _create_single_choice_facet,
    _create_toggle_facet,
    facet_modifier_map,
    filter_type_map,
    types_alias_map,
)


class FakeArgs:
    def __init__(self, data: dict[str, list[str] | str] | None = None):
        self._data = data or {}

    def getlist(self, key: str, default=None):
        if key not in self._data:
            return default or []
        val = self._data[key]
        if isinstance(val, list):
            return val
        return [val]

    def get(self, key: str, default=None):
        vals = self.getlist(key, None)
        if vals is None or len(vals) == 0:
            return default
        return vals[0]


def make_config() -> dict:
    return {
        "search": {
            "default_mode": "sources",
            "rows": 20,
            "page_sizes": [10, 20, 50],
            "modes": {
                "sources": {
                    "record_type": "source",
                    "q_fields": [{"alias": "name", "field": "name_t"}],
                    "filters": [
                        {
                            "alias": "year",
                            "type": "range",
                            "field": "year_i",
                            "label": "Year",
                        },
                        {
                            "alias": "is-online",
                            "type": "toggle",
                            "field": "online_b",
                            "active_value": "false",
                            "label": "Online",
                        },
                        {
                            "alias": "source-type",
                            "type": "select",
                            "field": "source_type_s",
                            "label": "Source Type",
                            "default_behaviour": "intersection",
                        },
                        {
                            "alias": "composer",
                            "type": "query",
                            "field": "composer_t",
                            "label": "Composer",
                        },
                    ],
                    "sorting": [
                        {
                            "alias": "relevance",
                            "solr_sort": ["score desc"],
                            "default": True,
                            "only_contents": False,
                        },
                        {
                            "alias": "alpha",
                            "solr_sort": ["name_sort asc"],
                            "default": False,
                            "only_contents": False,
                        },
                    ],
                },
                "incipits": {
                    "record_type": "incipit",
                    "q_fields": [{"alias": "text", "field": "text"}],
                    "filters": [],
                    "sorting": [
                        {
                            "alias": "relevance",
                            "solr_sort": ["score desc"],
                            "default": True,
                            "only_contents": False,
                        }
                    ],
                },
            },
        }
    }


def make_req(data: dict[str, list[str] | str] | None = None):
    cfg = make_config()
    args = FakeArgs(data)
    return SimpleNamespace(args=args, app=SimpleNamespace(ctx=SimpleNamespace(config=cfg)))


def test_validate_rejects_multiple_q():
    req = make_req({"q": ["a", "b"]})
    with pytest.raises(InvalidQueryException, match="Only one query parameter"):
        SearchRequest(req)


def test_validate_rejects_invalid_mode():
    req = make_req({"mode": "does-not-exist"})
    with pytest.raises(InvalidQueryException, match="Invalid value for the requested mode"):
        SearchRequest(req)


def test_validate_rejects_malformed_filter():
    req = make_req({"fq": "badfilter"})
    with pytest.raises(InvalidQueryException, match="Malformed filter query"):
        SearchRequest(req)


def test_compile_query_defaults_when_absent():
    sr = SearchRequest(make_req())
    assert sr._compile_query() == DEFAULT_QUERY_STRING
    assert sr.query_report == {"valid": True, "message": {"none": ["The query was valid"]}}


def test_compile_query_uses_parser(monkeypatch):
    sr = SearchRequest(make_req({"q": "name:bach"}))
    monkeypatch.setattr(
        "search_server.helpers.search_request.parse_with_field_replacements",
        lambda *_args, **_kwargs: "name_t:bach",
    )
    assert sr._compile_query() == "name_t:bach"
    assert sr.query_report["valid"] is True


@pytest.mark.parametrize(
    ("exc_cls", "expected_msg"),
    [
        (QueryParseError, "There was a problem parsing the query"),
        (FieldNotFoundError, "bad field"),
        (EmptyFieldQueryError, "empty field"),
    ],
)
def test_compile_query_handles_parser_errors(monkeypatch, exc_cls, expected_msg):
    sr = SearchRequest(make_req({"q": "broken"}))

    def _raiser(*_args, **_kwargs):
        raise exc_cls(expected_msg)

    monkeypatch.setattr(
        "search_server.helpers.search_request.parse_with_field_replacements", _raiser
    )
    assert sr._compile_query() == "broken"
    assert sr.query_report["valid"] is False
    assert expected_msg in sr.query_report["message"]["none"][0]


def test_compile_filters_handles_union_toggle_and_query_escaping():
    req = make_req(
        {
            "fq": [
                "source-type:Print",
                "source-type:Manuscript",
                "is-online:true",
                "composer:Bach/Handel",
            ],
            "fb": ["source-type:union"],
        }
    )
    sr = SearchRequest(req)
    filters = sr._compile_filters()
    assert "{!tag=SELECT_FILTER cost=80}source_type_s:(Print OR Manuscript)" in filters
    assert "online_b:(false)" in filters
    assert any("{!complexphrase inOrder=true}composer_t:" in f for f in filters)


def test_compile_filters_adds_incipit_parent_filter():
    req = make_req({"mode": "incipits"})
    sr = SearchRequest(req)
    filters = sr._compile_filters()
    assert "{!tag=MODE_FILTER}parent_type_s:source" in filters


def test_compile_adds_mode_filter_unless_manual_type():
    req = make_req({"fq": "source-type:Print"})
    sr = SearchRequest(req)
    query = sr.compile()
    assert any("{!tag=MODE_FILTER}type:source" == f for f in query["filter"])

    req_with_manual_type = make_req({"fq": ["source-type:Print", "source-type:type:person"]})
    sr2 = SearchRequest(req_with_manual_type)
    sr2.filters = ["type:person"]
    query2 = sr2.compile()
    assert "{!tag=MODE_FILTER}type:source" not in query2["filter"]


def test_compile_probe_sets_limit_zero():
    req = make_req()
    sr = SearchRequest(req, probe=True)
    query = sr.compile()
    assert query["limit"] == 0


def test_compile_adds_national_collection_filter():
    req = make_req({"nc": "CH"})
    sr = SearchRequest(req)
    query = sr.compile()
    assert 'country_codes_sm:"CH"' in query["filter"]


def test_incipit_mode_adds_scoring_query(monkeypatch):
    req = make_req({"mode": "incipits", "n": "PAE:dummy", "q": "text:abc"})
    monkeypatch.setattr(
        "search_server.helpers.search_request.get_pae_features",
        lambda _req: {
            "intervalsChromatic": [1, 2, 3],
            "pitchesChromatic": ["c", "d", "e"],
            "intervalRefinedContour": ["U", "D"],
        },
    )
    sr = SearchRequest(req)
    query = sr.compile()
    assert "qq" in query["params"]
    assert any("custom_score:scale(" in field for field in query["fields"])
    assert query["sort"].endswith("desc")


def test_helper_maps_and_facet_factory_functions():
    filters_cfg = [
        {"alias": "a", "type": "select", "field": "a_s"},
        {"alias": "b", "type": "toggle", "field": "b_b"},
    ]
    assert filter_type_map(filters_cfg) == {"a": "select", "b": "toggle"}
    assert types_alias_map(filters_cfg) == {"select": ["a"], "toggle": ["b"]}
    assert facet_modifier_map(["a:union", "b:intersection"]) == {
        "a": "union",
        "b": "intersection",
    }
    assert _create_range_facet({"field": "year_i"})["facet"]["min"] == "min(year_i)"
    assert _create_toggle_facet({"field": "online_b"})["field"] == "online_b"
    assert _create_select_facet({"field": "source_type_s"}, FacetBehaviourValues.UNION)[
        "domain"
    ]["excludeTags"] == ["SELECT_FILTER"]
    assert _create_parameter_facet({"field": "foo"}) == {
        "type": "terms",
        "field": "foo",
        "limit": 0,
    }
    assert _create_single_choice_facet({"field": "bar"})["limit"] == 2
