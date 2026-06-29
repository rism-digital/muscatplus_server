# ruff: noqa: S101

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyoxigraph import RdfFormat, parse

from linked_data.export import (
    DEFAULT_SOLR_SORT,
    build_parser,
    clean_output_for_types,
    expand_json_fields,
    failure_report_path,
    serialize_doc,
    shard_extension,
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


def test_turtle_conversion_declares_rismrel_prefix_when_relationship_role_is_used():
    doc = {
        "@context": {
            "@vocab": "https://rism.online/api/v1#",
            "rism": "https://rism.online/api/v1#",
            "rismrel": "https://rism.online/vocabulary/relationship/#",
            "dcterms": "http://purl.org/dc/terms/",
            "id": "@id",
            "type": "@type",
            "relationships": {
                "@id": "rism:relationships",
                "@type": "@id",
                "@context": {
                    "items": {"@id": "rism:hasRelationship", "@container": "@set"},
                    "role": {"@id": "rism:hasRole", "@type": "@vocab"},
                    "relatedTo": {"@id": "dcterms:relation", "@type": "@id"},
                },
            },
        },
        "id": "https://rism.online/people/1",
        "type": "rism:Person",
        "relationships": {
            "items": [
                {
                    "role": "rismrel:mother_of",
                    "relatedTo": "https://rism.online/people/2",
                }
            ]
        },
    }

    turtle = to_turtle(doc)

    assert "@prefix rismrel:" in turtle
    assert "rismrel:mother_of" in turtle
    assert "<https://rism.online/vocabulary/relationship/#mother_of>" not in turtle


def test_jsonld_included_materializes_class_labels_without_instance_type_label():
    doc = {
        "@context": {
            "rism": "https://rism.online/api/v1#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "id": "@id",
            "type": "@type",
            "included": "@included",
            "typeLabel": None,
            "label": {
                "@id": "rdfs:label",
                "@container": ["@language", "@set"],
            },
        },
        "id": "https://rism.online/people/1",
        "type": "rism:Person",
        "typeLabel": {"en": ["Person"]},
        "label": {"none": ["Example person"]},
        "included": [{"id": "rism:Person", "label": {"en": ["Person"]}}],
    }

    ntriples = to_ntriples(doc)

    assert '<https://rism.online/people/1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://rism.online/api/v1#Person> .' in ntriples
    assert '<https://rism.online/api/v1#Person> <http://www.w3.org/2000/01/rdf-schema#label> "Person"@en .' in ntriples
    assert "typeLabel" not in ntriples


def test_turtle_conversion_falls_back_when_pretty_printer_panics():
    class PanicException(BaseException):
        pass

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

    with patch(
        "search_server.helpers.linked_data.format_turtle",
        side_effect=PanicException("formatter panic"),
    ):
        turtle = to_turtle(doc)

    assert "@prefix rism:" in turtle
    assert "rism:Source" in turtle


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
    assert shard_tmp_path(tmp_path, "source", 2, "nt") == (
        tmp_path / "source" / "part-00002.nt.tmp"
    )
    assert shard_final_path(tmp_path, "source", 2, "nt") == (
        tmp_path / "source" / "part-00002.nt"
    )
    assert shard_tmp_path(tmp_path, "source", 2, "ttl") == (
        tmp_path / "source" / "part-00002.ttl.tmp"
    )
    assert shard_final_path(tmp_path, "source", 2, "ttl") == (
        tmp_path / "source" / "part-00002.ttl"
    )
    assert failure_report_path(tmp_path, "source", 2) == (
        tmp_path / "source" / "failed-records-00002.jsonl"
    )


def test_shard_extension_rejects_unknown_format():
    with pytest.raises(ValueError, match="Unsupported RDF output format"):
        shard_extension("rdfxml")


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

    clean_output_for_types(tmp_path, ["source"], "nt")

    assert not generated[0].exists()
    assert not generated[1].exists()
    assert not generated[2].exists()
    assert generated[3].exists()
    assert keep.exists()


def test_clean_output_for_types_only_removes_selected_format(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    ttl_path = source_dir / "part-00000.ttl"
    ttl_tmp_path = source_dir / "part-00000.ttl.tmp"
    nt_path = source_dir / "part-00000.nt"
    keep = source_dir / "notes.txt"
    for path in [ttl_path, ttl_tmp_path, nt_path, keep]:
        path.write_text("x")

    clean_output_for_types(tmp_path, ["source"], "ttl")

    assert not ttl_path.exists()
    assert not ttl_tmp_path.exists()
    assert nt_path.exists()
    assert keep.exists()


def test_serialize_doc_uses_turtle_output_when_requested():
    class AwaitableSerialized:
        def __init__(self, payload):
            self.payload = payload

        def __await__(self):
            async def _resolve():
                return self.payload

            return _resolve().__await__()

    class StubSerializer:
        def __init__(self, doc, context):
            self.serialized = AwaitableSerialized(
                {
                    "id": doc["id"],
                    "type": "rism:Source",
                    "label": {"en": ["Example source"]},
                }
            )

    doc = {"id": "https://rism.online/sources/1"}
    ctx_val = {
        "@context": {
            "rism": "https://rism.online/api/v1#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "id": "@id",
            "type": "@type",
            "label": {
                "@id": "rdfs:label",
                "@container": ["@language", "@set"],
            },
        }
    }

    output, timings = asyncio.run(
        serialize_doc(
            doc,
            StubSerializer,
            ctx_val,
            SimpleNamespace(),
            "ttl",
        )
    )

    assert "@prefix rism:" in output
    assert "rism:Source" in output
    assert timings.convert_seconds >= 0


def test_serialize_doc_rejects_missing_turtle_output():
    class AwaitableSerialized:
        def __init__(self, payload):
            self.payload = payload

        def __await__(self):
            async def _resolve():
                return self.payload

            return _resolve().__await__()

    class StubSerializer:
        def __init__(self, doc, context):
            self.serialized = AwaitableSerialized({"id": doc["id"]})

    with patch("linked_data.export.to_turtle_pyoxigraph", return_value=None):
        with pytest.raises(ValueError, match="No Turtle output"):
            asyncio.run(
                serialize_doc(
                    {"id": "https://rism.online/sources/1"},
                    StubSerializer,
                    {"@context": {}},
                    SimpleNamespace(),
                    "ttl",
                )
            )


def test_build_parser_accepts_ttl_and_nt_formats():
    parser = build_parser()

    assert parser.parse_args(["--format", "ttl"]).format == "ttl"
    assert parser.parse_args(["--format", "nt"]).format == "nt"


def test_build_parser_rejects_unknown_format():
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--format", "rdfxml"])


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
