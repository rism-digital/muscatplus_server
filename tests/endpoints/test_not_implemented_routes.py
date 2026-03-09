from __future__ import annotations

import pytest


NOT_IMPLEMENTED_CASES = [
    ("/countries/CH", "Not implemented"),
    ("/external/diamm/source/123/holding/456", "Not implemented"),
    ("/incipits/inc-1", "Not implemented"),
    ("/institutions", "Not implemented"),
    ("/institutions/123/relationships", "Not implemented"),
    ("/institutions/123/relationships/999", "Not implemented"),
    ("/institutions/123/digital-objects", "Not implemented"),
    ("/institutions/123/digital-objects/456", "Not implemented"),
    ("/people", "Not implemented"),
    ("/people/123/relationships", "Not implemented"),
    ("/people/123/relationships/999", "Not implemented"),
    ("/people/123/digital-objects", "Not implemented"),
    ("/people/123/digital-objects/456", "Not implemented"),
    ("/places", "Not implemented"),
    ("/places/123/relationships/999", "Not implemented"),
    ("/subjects", "Not implemented"),
    ("/works/123/incipits", "Not implemented"),
    ("/works/123/incipits/1", "Not Implemented"),
    ("/sources/123/creator", "Not implemented"),
    ("/sources/123/relationships", "Not implemented"),
    ("/sources/123/relationships/999", "Not implemented"),
    ("/sources/123/material-groups", "Not implemented"),
    ("/sources/123/material-groups/88", "Not implemented"),
    ("/sources/123/material-groups/88/relationships", "Not implemented"),
    ("/sources/123/digital-objects", "Not implemented"),
    ("/sources/123/digital-objects/456", "Not implemented"),
    ("/sources/123/holdings/321/relationships", "Not implemented"),
    ("/sources/123/holdings/321/digital-objects", "Not implemented"),
    ("/sources/123/holdings/321/digital-objects/456", "Not implemented"),
    ("/sources/123/inventory-items", "Not implemented"),
    ("/sources/123/inventory-items/654", "Not implemented"),
]


@pytest.mark.endpoint
@pytest.mark.contract
@pytest.mark.parametrize(("path", "message"), NOT_IMPLEMENTED_CASES)
def test_not_implemented_routes_are_locked(client, path: str, message: str):
    _, resp = client.get(path)
    assert resp.status == 501
    assert resp.json == {"message": message}
