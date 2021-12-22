import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import EXTERNAL_IDS
from search_server.helpers.serializers import ContextDictSerializer


class ExternalAuthoritiesSection(ContextDictSerializer):
    label = serpy.MethodField()
    etype = StaticField(
        label="type",
        value="rism:ExternalAuthoritiesSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: list) -> dict:
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.other_standard_identifier")

    def get_items(self, obj: list) -> list[dict]:
        externals: list = []
        for ext in obj:
            source, ident = ext.split(":")
            base = EXTERNAL_IDS.get(source)
            if not base:
                continue

            label: str = base["label"]
            uri: str = base["ident"].format(ident=ident)

            externals.append({
                "url": uri,
                "label": {"none": [label]},
                "type": "rism:ExternalAuthority"
            })

        return externals
