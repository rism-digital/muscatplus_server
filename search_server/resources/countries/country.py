import ypres

from shared_helpers.display_translators import (
    SOURCE_SIGLA_COUNTRY_MAP,
    country_code_labels_translator,
)


async def handle_country_request(req, country_id: str) -> dict | None:
    # Placeholder
    # fq: list = ["type:place"]
    return None


async def handle_country_list_request(req) -> dict | None:
    return CountryList(
        SOURCE_SIGLA_COUNTRY_MAP, context={"request": req, "direct_request": True}
    ).serialized


class CountryList(ypres.DictSerializer):
    clid = ypres.MethodField(label="id")
    cltype = ypres.StaticField(label="type", value="rism:CountryListResults")

    items = ypres.MethodField()

    def get_clid(self, _) -> str:
        req = self.context["request"]
        return req.url

    def get_items(self, obj: dict) -> list[dict]:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return [
            {"label": country_code_labels_translator(c, transl), "value": c}
            for c in obj
            if c
        ]
