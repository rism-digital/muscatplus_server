import ypres

from search_server.helpers.identifiers import EXTERNAL_IDS, get_identifier


class ExternalAuthoritiesSection(ypres.DictSerializer):
    sid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    etype = ypres.StaticField(label="type", value="rism:ExternalAuthoritiesSection")
    items = ypres.MethodField()

    def get_sid(self, obj: dict) -> str | None:
        req = self.context["request"]
        route_name = self.context["section_route"]
        route_params = self.context["route_params"]

        return get_identifier(req, route_name, **route_params)

    def get_slabel(self, obj: dict) -> dict:
        req = self.context["request"]  # type: ignore
        transl: dict = req.ctx.translations  # type: ignore

        return transl.get("records.other_standard_identifier", {})

    def get_items(self, obj: dict) -> list[dict]:
        externals: list = []
        external_ids: list = obj["external_ids"]
        for ext in external_ids:
            source, ident = ext.split(":", 1)
            base = EXTERNAL_IDS.get(source)
            if not base:
                continue

            label: str = base["label"]
            uri_tmpl: str | None = base.get("ident")
            full_label: str = f"{label}: {ident}"

            record: dict = {}
            req = self.context["request"]
            route_name = self.context.get("item_route")
            route_params = self.context["route_params"]
            if isinstance(route_name, str):
                new_route_params = {**route_params, "authority_id": ext}
                record["id"] = get_identifier(req, route_name, **new_route_params)

            # Do this first so the URL field appears first in the dictionary
            if uri_tmpl:
                uri: str = uri_tmpl.format(ident=ident)
                record["url"] = uri
                # remove the {ident} placeholder to get the base URI
                record["base"] = uri_tmpl[:-7]

            record.update(
                {
                    "label": {"none": [full_label]},
                    "value": f"{ident}",
                    "type": "rism:ExternalAuthority",
                }
            )

            externals.append(record)

        return externals
