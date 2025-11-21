import orjson

from search_server.helpers.display_translators import SOURCE_SIGLA_COUNTRY_MAP
from search_server.resources.countries.country import CountryList


def render_template(app_context, req, data_obj: dict | None) -> str:
    record_tmpl = app_context.template_env.get_template("main.html.j2")
    country_list: dict = CountryList(
        SOURCE_SIGLA_COUNTRY_MAP, context={"request": req, "direct_request": True}
    ).serialized

    tmpl_vars = {
        "record_data": orjson.dumps(data_obj).decode("utf-8"),
        "country_list_data": orjson.dumps(country_list).decode("utf-8"),
    }

    return record_tmpl.render(**tmpl_vars)
