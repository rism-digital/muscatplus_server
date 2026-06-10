# ruff: noqa: S101

from __future__ import annotations

import json

from pyoxigraph import RdfFormat, parse

from linked_data.export import (
    DEFAULT_SOLR_SORT,
    clean_output_for_types,
    expand_json_fields,
    failure_report_path,
    shard_final_path,
    shard_tmp_path,
    solr_request_limit,
    solr_sort,
    to_ntriples_pyoxigraph,
    write_manifest,
)
from search_server.helpers.linked_data import to_ntriples, to_turtle


def quads_from_ntriples(ntriples: str):
    return set(
        parse(
            input=ntriples.encode("utf-8"),
            format=RdfFormat.N_TRIPLES,
            without_named_graphs=True,
        )
    )


def test_export_new_uses_shared_pyoxigraph_conversion():
    doc = {
        "@context": {
            "rism": "https://rism.online/api/v1#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "id": "@id",
            "type": "@type",
            "label": {
                "@id": "rdfs:label",
                "@container": ["@language", "@set"],
            },
            "items": {"@id": "rism:hasMaterialGroup", "@container": "@set"},
        },
        "id": "https://rism.online/sources/1",
        "type": "rism:Source",
        "label": {"en": ["Example source"]},
        "items": [
            {
                "id": "https://rism.online/sources/1/material-groups/01",
                "type": "rism:MaterialGroup",
                "label": {"none": ["Group 01"]},
            }
        ],
    }

    assert quads_from_ntriples(to_ntriples(doc)) == quads_from_ntriples(
        to_ntriples_pyoxigraph(doc)
    )


def test_pyoxigraph_conversion_handles_section_item_predicates():
    doc = {
        "@context": {
            "@vocab": "https://rism.online/api/v1#",
            "rism": "https://rism.online/api/v1#",
            "relators": "http://id.loc.gov/vocabulary/relators/",
            "id": "@id",
            "relationships": {
                "@id": "rism:relationships",
                "@type": "@id",
                "@context": {
                    "items": {"@id": "rism:hasRelationship", "@container": "@set"},
                    "role": {"@id": "rism:hasRole", "@type": "@vocab"},
                },
            },
        },
        "id": "https://rism.online/sources/1",
        "relationships": {
            "items": [{"role": "relators:cre"}],
            "sectionLabel": {"en": ["Relationships"]},
        },
    }

    quads = quads_from_ntriples(to_ntriples_pyoxigraph(doc))
    predicates = {quad.predicate.value for quad in quads}

    assert "https://rism.online/api/v1#relationships" in predicates
    assert "https://rism.online/api/v1#hasRelationship" in predicates


def test_turtle_conversion_emits_turtle_not_ntriples():
    doc = {
        "@context": {
            "rism": "https://rism.online/api/v1#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "id": "@id",
            "type": "@type",
            "label": {
                "@id": "rdfs:label",
                "@container": ["@language", "@set"],
            },
        },
        "id": "https://rism.online/sources/1",
        "type": "rism:Source",
        "label": {"en": ["Example source"]},
    }

    turtle = to_turtle(doc)

    assert "@prefix rism:" in turtle
    assert "rism:Source" in turtle
    assert "\n\n<https://rism.online/sources/1>" in turtle
    assert quads_from_ntriples(to_ntriples(doc)) == set(
        parse(
            input=turtle.encode("utf-8"),
            format=RdfFormat.TURTLE,
            without_named_graphs=True,
        )
    )


def test_expand_json_fields_parses_single_and_multi_values():
    doc = {
        "id": "source_1",
        "title_json": '{"value":"Title"}',
        "external_records_jsonm": ['{"id":"1"}', '{"id":"2"}'],
    }

    expanded, elapsed = expand_json_fields(doc)

    assert elapsed >= 0
    assert expanded["title_json"] == {"value": "Title"}
    assert expanded["external_records_jsonm"] == [{"id": "1"}, {"id": "2"}]
    assert doc["title_json"] == '{"value":"Title"}'


def test_shard_paths_are_worker_owned(tmp_path):
    assert shard_tmp_path(tmp_path, "source", 2) == (
        tmp_path / "source" / "part-00002.nt.tmp"
    )
    assert shard_final_path(tmp_path, "source", 2) == (
        tmp_path / "source" / "part-00002.nt"
    )
    assert failure_report_path(tmp_path, "source", 2) == (
        tmp_path / "source" / "failed-records-00002.jsonl"
    )


def test_write_manifest_records_totals(tmp_path):
    write_manifest(
        tmp_path,
        [
            {
                "records_seen": 3,
                "records_succeeded": 2,
                "records_failed": 1,
            },
            {
                "records_seen": 4,
                "records_succeeded": 4,
                "records_failed": 0,
            },
        ],
    )

    manifest = json.loads((tmp_path / "manifest.json").read_text())

    assert manifest["totals"] == {
        "records_seen": 7,
        "records_succeeded": 6,
        "records_failed": 1,
    }


def test_clean_output_for_types_removes_generated_shards_only(tmp_path):
    source_dir = tmp_path / "source"
    person_dir = tmp_path / "person"
    source_dir.mkdir()
    person_dir.mkdir()
    generated = [
        source_dir / "part-00000.nt",
        source_dir / "part-00000.nt.tmp",
        source_dir / "failed-records-00000.jsonl",
        person_dir / "part-00000.nt",
    ]
    keep = source_dir / "notes.txt"
    for path in [*generated, keep]:
        path.write_text("x")

    clean_output_for_types(tmp_path, ["source"])

    assert not generated[0].exists()
    assert not generated[1].exists()
    assert not generated[2].exists()
    assert generated[3].exists()
    assert keep.exists()


def test_solr_sort_defaults_to_stable_id_sort():
    assert solr_sort(randomize=False, random_seed=None) == DEFAULT_SOLR_SORT


def test_solr_sort_uses_random_seed_with_id_tiebreaker():
    assert solr_sort(randomize=True, random_seed=12345) == "random_12345 asc,id asc"


def test_solr_sort_requires_seed_for_random_sort():
    try:
        solr_sort(randomize=True, random_seed=None)
    except ValueError as err:
        assert "random seed" in str(err)
    else:
        raise AssertionError("Expected random Solr sort to require a seed")


def test_solr_request_limit_respects_smaller_export_limit():
    assert solr_request_limit(page_size=1000, limit=100) == 100
    assert solr_request_limit(page_size=1000, limit=2000) == 1000
    assert solr_request_limit(page_size=1000, limit=None) == 1000
