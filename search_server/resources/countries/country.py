from typing import Optional

import serpy

from search_server.helpers.display_translators import SOURCE_SIGLA_COUNTRY_MAP, country_code_labels_translator
from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer


async def handle_country_request(req, country_id: str) -> Optional[dict]:
    # Placeholder
    fq: list = ["type:place"]
    return None


async def handle_country_list_request(req) -> Optional[dict]:
    return CountryList(SOURCE_SIGLA_COUNTRY_MAP, context={"request": req,
                                                          "direct_request": True}).data


class CountryList(JSONLDContextDictSerializer):
    clid = serpy.MethodField(
        label="id"
    )
    cltype = StaticField(
        label="type",
        value="rism:CountryListResults"
    )

    items = serpy.MethodField()

    def get_clid(self, _) -> str:
        req = self.context.get("request")
        return req.url

    def get_items(self, obj: dict) -> list[dict]:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        res: list = []

        for country_code in obj.keys():
            # Skip the 'None' entry
            if not country_code:
                continue

            res.append({
                "label": country_code_labels_translator(country_code, transl),
                "value": country_code
            })

        return res
