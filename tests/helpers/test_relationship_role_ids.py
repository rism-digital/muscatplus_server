from search_server.resources.shared.relationship import _canonical_role_id


def test_canonical_role_id_maps_loc_relator_code_to_loc_uri() -> None:
    assert _canonical_role_id("cmp") == "http://id.loc.gov/vocabulary/relators/cmp"
    assert _canonical_role_id("relators:aut") == "http://id.loc.gov/vocabulary/relators/aut"


def test_canonical_role_id_maps_rdau_code_to_full_rda_uri() -> None:
    assert _canonical_role_id("rdau:P60191") == "http://rdaregistry.info/Elements/u/P60191"


def test_canonical_role_id_maps_family_relationship_to_rism_vocab() -> None:
    assert (
        _canonical_role_id("father of")
        == "https://rism.online/vocabulary/relationship/father_of"
    )
    assert (
        _canonical_role_id("relators:father_of")
        == "https://rism.online/vocabulary/relationship/father_of"
    )
