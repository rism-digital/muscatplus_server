from typing import Optional

import serpy

from shared_helpers.display_translators import SOURCE_SIGLA_COUNTRY_MAP, country_code_labels_translator


async def handle_country_request(req, country_id: str) -> Optional[dict]:
    # Placeholder
    fq: list = ["type:place"]
    return None


async def handle_country_list_request(req) -> Optional[dict]:  # type: ignore
    return CountryList(SOURCE_SIGLA_COUNTRY_MAP, context={"request": req,
                                                          "direct_request": True}).data


class CountryList(serpy.DictSerializer):
    clid = serpy.MethodField(
        label="id"
    )
    cltype = serpy.StaticField(
        label="type",
        value="rism:CountryListResults"
    )

    items = serpy.MethodField()

    def get_clid(self, _) -> str:
        req = self.context.get("request")  # type: ignore
        return req.url

    def get_items(self, obj: dict) -> list[dict]:
        req = self.context.get("request")  # type: ignore
        transl: dict = req.ctx.translations

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
