from __future__ import annotations

import pytest


NOT_IMPLEMENTED_CASES = [
    ("/countries/CH", "Not implemented"),
    ("/external/diamm/source/123/holding/456", "Not implemented"),
    ("/incipits/inc-1", "Not implemented"),
    ("/institutions", "Not implemented"),
    ("/institutions/123/external-authorities", "Not implemented"),
    ("/institutions/123/external-authorities/auth-1", "Not implemented"),
    ("/institutions/123/notes", "Not implemented"),
    ("/institutions/123/relationships", "Not implemented"),
    ("/institutions/123/relationships/999", "Not implemented"),
    ("/institutions/123/digital-objects", "Not implemented"),
    ("/institutions/123/digital-objects/456", "Not implemented"),
    ("/people", "Not implemented"),
    ("/people/123/external-authorities", "Not implemented"),
    ("/people/123/external-authorities/auth-1", "Not implemented"),
    ("/people/123/notes", "Not implemented"),
    ("/people/123/relationships", "Not implemented"),
    ("/people/123/relationships/999", "Not implemented"),
    ("/people/123/digital-objects", "Not implemented"),
    ("/people/123/digital-objects/456", "Not implemented"),
    ("/places", "Not implemented"),
    ("/places/123/relationships/999", "Not implemented"),
    ("/publications/123/notes", "Not implemented"),
    ("/publications/123/relationships", "Not implemented"),
    ("/publications/123/relationships/999", "Not implemented"),
    ("/subjects", "Not implemented"),
    ("/works/123/external-authorities", "Not implemented"),
    ("/works/123/external-authorities/auth-1", "Not implemented"),
    ("/works/123/incipits", "Not implemented"),
    ("/works/123/incipits/1", "Not Implemented"),
    ("/works/123/liturgical-festivals", "Not implemented"),
    ("/works/123/performance-locations", "Not implemented"),
    ("/works/123/references-notes", "Not implemented"),
    ("/works/123/relationships", "Not implemented"),
    ("/works/123/relationships/999", "Not implemented"),
    ("/sources/123/creator", "Not implemented"),
    ("/sources/123/relationships", "Not implemented"),
    ("/sources/123/relationships/999", "Not implemented"),
    ("/sources/123/references-notes", "Not implemented"),
    ("/sources/123/performance-locations", "Not implemented"),
    ("/sources/123/liturgical-festivals", "Not implemented"),
    ("/sources/123/material-groups", "Not implemented"),
    ("/sources/123/material-groups/88", "Not implemented"),
    ("/sources/123/material-groups/88/relationships", "Not implemented"),
    ("/sources/123/material-groups/88/relationships/999", "Not implemented"),
    ("/sources/123/digital-objects", "Not implemented"),
    ("/sources/123/digital-objects/456", "Not implemented"),
    ("/sources/123/holdings/321/relationships", "Not implemented"),
    ("/sources/123/holdings/321/relationships/999", "Not implemented"),
    ("/sources/123/holdings/321/digital-objects", "Not implemented"),
    ("/sources/123/holdings/321/digital-objects/456", "Not implemented"),
    ("/sources/123/inventory-items/654/relationships", "Not implemented"),
    ("/sources/123/inventory-items/654/relationships/999", "Not implemented"),
    ("/sources/123/inventory-items/654/references-notes", "Not implemented"),
    ("/sources/123/inventory-items/654/performance-locations", "Not implemented"),
    ("/sources/123/inventory-items/654/liturgical-festivals", "Not implemented"),
]


@pytest.mark.endpoint
@pytest.mark.contract
@pytest.mark.parametrize(("path", "message"), NOT_IMPLEMENTED_CASES)
def test_not_implemented_routes_are_locked(client, path: str, message: str):
    _, resp = client.get(path)
    assert resp.status == 501
    assert resp.json == {"message": message}
