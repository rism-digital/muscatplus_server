from typing import Optional

import serpy

from shared_helpers.identifiers import EXTERNAL_IDS


class ExternalAuthoritiesSection(serpy.DictSerializer):
    label = serpy.MethodField()
    etype = serpy.StaticField(
        label="type",
        value="rism:ExternalAuthoritiesSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: list) -> dict:
        req = self.context.get("request")  # type: ignore
        transl: dict = req.app.ctx.translations  # type: ignore

        return transl.get("records.other_standard_identifier", {})

    def get_items(self, obj: list) -> list[dict]:
        externals: list = []
        for ext in obj:
            source, ident = ext.split(":", 1)
            base = EXTERNAL_IDS.get(source)
            if not base:
                continue

            label: str = base["label"]
            uri_tmpl: Optional[str] = base.get("ident")
            full_label: str = f"{label}: {ident}"

            record: dict = {}

            # Do this first so the URL field appears first in the dictionary
            if uri_tmpl:
                uri: str = uri_tmpl.format(ident=ident)
                record["url"] = uri

            record.update({
                "label": {"none": [full_label]},
                "type": "rism:ExternalAuthority"
            })

            externals.append(record)

        return externals
