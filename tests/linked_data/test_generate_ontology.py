# ruff: noqa: S101

from __future__ import annotations

from pyoxigraph import Literal, NamedNode, RdfFormat, parse

from linked_data import generate_ontology


def quads_from_turtle(turtle: str):
    return set(
        parse(
            input=turtle.encode("utf-8"),
            format=RdfFormat.TURTLE,
            without_named_graphs=True,
        )
    )


def quads_from_ntriples(ntriples: str):
    return set(
        parse(
            input=ntriples.encode("utf-8"),
            format=RdfFormat.N_TRIPLES,
            without_named_graphs=True,
        )
    )


def test_generate_ontology_emits_key_derived_properties():
    quads = quads_from_turtle(generate_ontology.serialize_ontology())

    assert (
        NamedNode("https://rism.online/api/v1#hasExternalAuthority"),
        NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        NamedNode("http://www.w3.org/2002/07/owl#ObjectProperty"),
    ) in {(quad.subject, quad.predicate, quad.object) for quad in quads}

    assert (
        NamedNode("https://schema.org/gender"),
        NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        NamedNode("http://www.w3.org/2002/07/owl#DatatypeProperty"),
    ) in {(quad.subject, quad.predicate, quad.object) for quad in quads}


def test_generate_ontology_emits_curated_class_mappings():
    triples = {(quad.subject, quad.predicate, quad.object) for quad in quads_from_turtle(generate_ontology.serialize_ontology())}

    assert (
        NamedNode("https://rism.online/api/v1#Person"),
        NamedNode("http://www.w3.org/2002/07/owl#equivalentClass"),
        NamedNode("http://xmlns.com/foaf/0.1/Person"),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#Institution"),
        NamedNode("http://www.w3.org/2002/07/owl#equivalentClass"),
        NamedNode("https://schema.org/Organization"),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#Place"),
        NamedNode("http://www.w3.org/2002/07/owl#equivalentClass"),
        NamedNode("https://schema.org/Place"),
    ) in triples


def test_generate_ontology_emits_relationship_property_mappings():
    triples = {(quad.subject, quad.predicate, quad.object) for quad in quads_from_turtle(generate_ontology.serialize_ontology())}

    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#mother_of"),
        NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        NamedNode("http://www.w3.org/2002/07/owl#ObjectProperty"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#mother_of"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
        NamedNode("https://rism.online/vocabulary/relationship/#parent_of"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#parent_of"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
        NamedNode("https://schema.org/children"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#sister_of"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
        NamedNode("https://rism.online/vocabulary/relationship/#sibling_of"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#sibling_of"),
        NamedNode("http://www.w3.org/2002/07/owl#equivalentProperty"),
        NamedNode("https://schema.org/sibling"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#married_to"),
        NamedNode("http://www.w3.org/2002/07/owl#equivalentProperty"),
        NamedNode("https://schema.org/spouse"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#related_to"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
        NamedNode("https://schema.org/knows"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#father_of"),
        NamedNode("http://www.w3.org/2002/07/owl#inverseOf"),
        NamedNode("https://rism.online/vocabulary/relationship/#child_of"),
    ) in triples


def test_generate_ontology_omits_unsafe_relationship_property_mappings():
    triples = {(quad.subject, quad.predicate, quad.object) for quad in quads_from_turtle(generate_ontology.serialize_ontology())}

    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#mother_of"),
        NamedNode("http://www.w3.org/2002/07/owl#equivalentProperty"),
        NamedNode("https://schema.org/children"),
    ) not in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#sister_of"),
        NamedNode("http://www.w3.org/2002/07/owl#equivalentProperty"),
        NamedNode("https://schema.org/sibling"),
    ) not in triples

    confused_with_subject = NamedNode("https://rism.online/vocabulary/relationship/#confused_with")
    other_subject = NamedNode("https://rism.online/vocabulary/relationship/#other")
    external_mapping_predicates = {
        NamedNode("http://www.w3.org/2002/07/owl#equivalentProperty"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
    }
    schemaorg_prefix = "https://schema.org/"

    assert not any(
        subject == confused_with_subject
        and predicate in external_mapping_predicates
        and isinstance(obj, NamedNode)
        and obj.value.startswith(schemaorg_prefix)
        for subject, predicate, obj in triples
    )
    assert not any(
        subject == other_subject
        and predicate in external_mapping_predicates
        and isinstance(obj, NamedNode)
        and obj.value.startswith(schemaorg_prefix)
        for subject, predicate, obj in triples
    )


def test_generate_ontology_emits_place_relationship_property_mappings():
    triples = {(quad.subject, quad.predicate, quad.object) for quad in quads_from_turtle(generate_ontology.serialize_ontology())}

    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#go"),
        NamedNode("http://www.w3.org/2002/07/owl#equivalentProperty"),
        NamedNode("https://schema.org/birthPlace"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#so"),
        NamedNode("http://www.w3.org/2002/07/owl#equivalentProperty"),
        NamedNode("https://schema.org/deathPlace"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#active_in"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
        NamedNode("https://schema.org/workLocation"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#wo"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
        NamedNode("https://rism.online/vocabulary/relationship/#active_in"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#wl"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
        NamedNode("https://rism.online/vocabulary/relationship/#active_in"),
    ) in triples
    assert (
        NamedNode("https://rism.online/vocabulary/relationship/#wr"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
        NamedNode("https://rism.online/vocabulary/relationship/#active_in"),
    ) in triples


def test_generate_ontology_keeps_ambiguous_place_relationships_local_only():
    triples = {(quad.subject, quad.predicate, quad.object) for quad in quads_from_turtle(generate_ontology.serialize_ontology())}
    external_mapping_predicates = {
        NamedNode("http://www.w3.org/2002/07/owl#equivalentProperty"),
        NamedNode("http://www.w3.org/2000/01/rdf-schema#subPropertyOf"),
    }
    schemaorg_prefix = "https://schema.org/"

    for subject in (
        NamedNode("https://rism.online/vocabulary/relationship/#ha"),
        NamedNode("https://rism.online/vocabulary/relationship/#xp"),
    ):
        assert not any(
            triple_subject == subject
            and predicate in external_mapping_predicates
            and isinstance(obj, NamedNode)
            and obj.value.startswith(schemaorg_prefix)
            for triple_subject, predicate, obj in triples
        )


def test_generate_ontology_check_detects_drift_and_matches_current_output(tmp_path):
    output_path = tmp_path / "ontology.ttl"
    output_path.write_text("out of date\n")

    assert generate_ontology.main(["--check", "--output", str(output_path)]) == 1

    output_path.write_text(generate_ontology.serialize_ontology())

    assert generate_ontology.main(["--check", "--output", str(output_path)]) == 0


def test_generate_ontology_supports_ntriples_output_and_check(tmp_path):
    output_path = tmp_path / "ontology.nt"
    output_path.write_text("out of date\n")

    assert (
        generate_ontology.main(
            ["--format", "nt", "--check", "--output", str(output_path)]
        )
        == 1
    )

    ntriples = generate_ontology.serialize_ontology("nt")
    output_path.write_text(ntriples)

    assert quads_from_ntriples(ntriples) == quads_from_turtle(
        generate_ontology.serialize_ontology()
    )
    assert (
        generate_ontology.main(
            ["--format", "nt", "--check", "--output", str(output_path)]
        )
        == 0
    )


def test_generate_ontology_preserves_header_metadata():
    quads = quads_from_turtle(generate_ontology.serialize_ontology())
    ontology = NamedNode("https://rism.online/api/v1#")
    triples = {(quad.subject, quad.predicate, quad.object) for quad in quads}

    assert (
        ontology,
        NamedNode("http://purl.org/dc/terms/title"),
        Literal("RISM service ontology", language="en"),
    ) in triples


def test_generate_ontology_adds_gender_query_guidance():
    triples = {
        (quad.subject, quad.predicate, quad.object)
        for quad in quads_from_turtle(generate_ontology.serialize_ontology())
    }
    gender = NamedNode("https://schema.org/gender")

    assert (
        gender,
        NamedNode("http://www.w3.org/2000/01/rdf-schema#domain"),
        NamedNode("https://rism.online/api/v1#Person"),
    ) in triples
    assert (
        gender,
        NamedNode("http://www.w3.org/2000/01/rdf-schema#range"),
        NamedNode("http://www.w3.org/2001/XMLSchema#string"),
    ) in triples
    assert (
        gender,
        NamedNode("http://www.w3.org/2000/01/rdf-schema#comment"),
        Literal(
            'Linked RISM person RDF exposes gender directly on the person resource as a plain string literal, for example "female" or "male".',
            language="en",
        ),
    ) in triples
    assert (
        gender,
        NamedNode("https://rism.online/api/v1#queryPattern"),
        Literal("?person schemaorg:gender ?gender ."),
    ) in triples
    assert (
        gender,
        NamedNode("https://rism.online/api/v1#queryPattern"),
        Literal('?person schemaorg:gender "female" .'),
    ) in triples
    assert (
        gender,
        NamedNode("https://rism.online/api/v1#queryPattern"),
        Literal('?person schemaorg:gender "male" .'),
    ) in triples


def test_generate_ontology_adds_person_and_common_property_query_guidance():
    triples = {
        (quad.subject, quad.predicate, quad.object)
        for quad in quads_from_turtle(generate_ontology.serialize_ontology())
    }
    query_pattern = NamedNode("https://rism.online/api/v1#queryPattern")

    assert (
        NamedNode("https://rism.online/api/v1#Person"),
        query_pattern,
        Literal(
            '?person a rism:Person ; rdfs:label ?name ; schemaorg:gender "female" . FILTER(LANG(?name) = "none")'
        ),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#hasSiglum"),
        query_pattern,
        Literal("?institution rism:hasSiglum ?siglum ."),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#hasCountryCodes"),
        query_pattern,
        Literal("?institution rism:hasCountryCodes ?countryCode ."),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#hasCountryCodes"),
        query_pattern,
        Literal(
            "?holding rism:hasHoldingInstitution/rism:hasCountryCodes ?countryCode ."
        ),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#hasRole"),
        query_pattern,
        Literal("?relationship dcterms:relation ?related ; rism:hasRole ?role ."),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#hasRole"),
        query_pattern,
        Literal("?relationship dcterms:relation ?person ; rism:hasRole relators:dte ."),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#hasRole"),
        query_pattern,
        Literal(
            "?relationship dcterms:relation ?publisher ; rism:hasRole relators:pbl ."
        ),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#sourceTypes"),
        query_pattern,
        Literal("?source rism:sourceTypes/rism:sourceType ?sourceType ."),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#sourceTypes"),
        query_pattern,
        Literal("?source rism:sourceTypes/rism:recordType ?recordType ."),
    ) in triples
    assert (
        NamedNode("https://rism.online/api/v1#sourceTypes"),
        query_pattern,
        Literal("?source rism:sourceTypes/rism:contentTypes ?contentType ."),
    ) in triples


def test_generate_ontology_avoids_unsupported_query_cookbook_advice():
    ontology = generate_ontology.serialize_ontology()

    assert "SAMPLE(" not in ontology
    assert "join labels later" not in ontology
