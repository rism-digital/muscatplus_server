import logging
from typing import Optional

import ypres

from search_server.helpers.record_types import create_record_block
from shared_helpers.identifiers import EXTERNAL_IDS, PROJECT_IDENTIFIERS
from shared_helpers.solr_connection import SolrResult

log = logging.getLogger("mp_server")


class ExternalResourcesSection(ypres.AsyncDictSerializer):
    """
    Returns a formatted object of external links.

    Note: `external_links_json` should be checked for presence
    in the Solr result before calling this, as we assume that if this is called there
    is at least one link!
    """
    section_label = ypres.MethodField(
        label="sectionLabel"
    )
    items = ypres.MethodField()
    external_records = ypres.MethodField(
        label="externalRecords"
    )
    # sites = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        return transl.get("records.related_resources", {})

    def get_items(self, obj: SolrResult) -> Optional[list[dict]]:
        if "external_resources" in obj:
            # If we're serializing from a JSON field, then this will be the key
            res = obj["external_resources"]
        elif "external_resources_json" in obj:
            # otherwise use the JSON field on the Solr document.
            res = obj["external_resources_json"]
        else:
            return None

        return ExternalResource(res, many=True,
                                context={"request": self.context.get("request")}).data

    def get_external_records(self, obj: dict) -> Optional[list[dict]]:
        if not obj.get("has_external_record_b", False):
            return None

        req = self.context.get("request")
        transl: dict = req.ctx.translations

        external_records = obj.get("external_records_jsonm", [])
        record_block = create_record_block("collection", "manuscript", ["musical"], transl)
        ret = []
        for r in external_records:
            proj: str = r["project"]
            ident: Optional[str] = EXTERNAL_IDS.get(proj, {}).get("ident")
            if not ident:
                continue

            sfx = f"sources/{r['id']}"

            # See the `ExternalRecord` class for the general structure of this block.
            # The "id" of this external record is not resolvable, so we use a urn to assign a
            # unique ID to be consistent with the resolvable form of the ExternalRecord..
            ret.append({
                "id": f"urn:rism:{proj}:{r['type']}:{r['id']}",
                "type": "rism:ExternalRecord",
                "project": PROJECT_IDENTIFIERS[proj],
                "record": {
                    "id": ident.format(ident=sfx),
                    "type": "rism:Source",
                    "typeLabel": transl.get("records.source"),
                    "record": record_block,
                    "label": {"none": [f"{r.get('label')}"]}
                }
            })

        return ret


class ExternalResource(ypres.DictSerializer):
    rtype = ypres.StaticField(
        label="type",
        value="rism:ExternalResource"
    )
    url = ypres.MethodField()
    label = ypres.MethodField()
    resource_type = ypres.MethodField(
        label="resourceType"
    )

    def get_url(self, obj: dict) -> Optional[str]:
        return obj.get("url")

    def get_label(self, obj: dict) -> dict:
        label: str

        if "note" in obj:
            label = obj["note"]
        elif "link_type" in obj:
            label = obj["link_type"]
        else:
            label = "[External Resource]"
        return {"none": [label]}

    def get_resource_type(self, obj: dict) -> str:
        rtype: str
        link_type: Optional[str] = obj.get("link_type")

        if link_type in ("IIIF", "IIIF manifest (digitized source)", "IIIF manifest (other)"):
            rtype = "IIIFManifestLink"
        elif link_type in ("Digitalization", "Digitized"):
            rtype = "DigitizationLink"
        else:
            rtype = "OtherLink"

        return f"rism:{rtype}"
