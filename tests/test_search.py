
from search_server.server import app


def test_search_base():
    request, response = app.test_client.get("/search")
    assert response.status == 200


def test_everything_mode():
    request, response = app.test_client.get("/search?mode=everything")
    assert response.status == 200


def test_all_other_modes():
    for mode in ["sources", "people", "institutions", "incipits"]:
        request, response = app.test_client.get(f"/search?mode={mode}")
        assert response.status == 200


def test_bad_mode():
    request, response = app.test_client.get("/search?mode=flimflam")
    assert response.status == 400


def test_bad_multiple_modes():
    request, response = app.test_client.get("/search?mode=everything&mode=sources")
    assert response.status == 400


def test_empty_mode_returns_success():
    # should return the same as mode=everything
    request, response = app.test_client.get("/search?mode=")
    assert response.status == 200


def test_empty_mode_with_filters():
    # should return the same as mode=everything, but with filters applied
    request, response = app.test_client.get("/search?fq=source-type:Print")
    assert response.status == 200


def test_bad_rows():
    request, response = app.test_client.get("/search?rows=X")
    assert response.status == 400


def test_bad_page():
    request, response = app.test_client.get("/search?page=Y")
    assert response.status == 400
