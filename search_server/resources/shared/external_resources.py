import ypres

from search_server.helpers.identifiers import EXTERNAL_IDS, PROJECT_IDENTIFIERS
from search_server.helpers.record_types import create_source_types_block
from search_server.helpers.solr_connection import SolrResult


class ExternalResourcesSection(ypres.DictSerializer):
    """
    Returns a formatted object of external links.

    Note: `external_links_json` should be checked for presence
    in the Solr result before calling this, as we assume that if this is called there
    is at least one link!
    """

    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()
    external_records = ypres.MethodField(label="externalRecords")
    # sites = ypres.MethodField()

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl.get("records.related_resources", {})

    def get_items(self, obj: SolrResult) -> list[dict] | None:
        if "external_resources" in obj:
            # If we're serializing from a JSON field, then this will be the key
            res = obj["external_resources"]
        elif "external_resources_json" in obj:
            # otherwise use the JSON field on the Solr document.
            res = obj["external_resources_json"]
        else:
            return None

        return ExternalResource(
            res, many=True, context={"request": self.context["request"]}
        ).serialized_many

    def get_external_records(self, obj: dict) -> list[dict] | None:
        if not obj.get("has_external_record_b", False):
            return None

        req = self.context["request"]
        transl: dict = req.ctx.translations

        external_records = obj.get("external_records_jsonm", [])
        ret = []

        for r in external_records:
            rec: dict | None = _create_external_record_link(r, transl)
            if not rec:
                continue

            ret.append(rec)

        return ret


def _create_external_record_link(record: dict, translations: dict) -> dict | None:
    project: str = record["project"]
    ident: str | None = EXTERNAL_IDS.get(project, {}).get("ident")
    if not ident:
        return None

    project_type: str | None = record.get("project_type")
    if not project_type:
        return None

    sfx = f"{project_type}/{record['id']}"
    record_type = record["type"]

    if record_type == "source":
        resource_type = "rism:Source"
        type_label = translations.get("records.source")
    elif record_type == "institution":
        resource_type = "rism:Institution"
        type_label = translations.get("records.institution")
    elif record_type == "person":
        resource_type = "rism:Person"
        type_label = translations.get("records.person")
    else:
        resource_type = "rism:Unknown"
        type_label = translations.get("records.unknown")

    resource_record = {
        "id": ident.format(ident=sfx),
        "type": resource_type,
        "typeLabel": type_label,
        "label": {"none": [f"{record.get('label')}"]},
    }

    if record_type == "source":
        resource_record["sourceTypes"] = (
            create_source_types_block(
                "collection", "manuscript", ["musical"], translations
            ),
        )

    return {
        "id": f"urn:rism:{project}:{record_type}:{record['id']}",
        "type": "rism:ExternalRecord",
        "project": PROJECT_IDENTIFIERS[project],
        "record": resource_record,
    }


class ExternalResource(ypres.DictSerializer):
    rtype = ypres.StaticField(label="type", value="rism:ExternalResource")
    url = ypres.MethodField()
    slabel = ypres.MethodField(label="label")
    resource_type = ypres.MethodField(label="resourceType")

    def get_url(self, obj: dict) -> str | None:
        return obj.get("url")

    def get_slabel(self, obj: dict) -> dict:
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
        link_type: str | None = obj.get("link_type")

        if link_type in (
            "IIIF",
            "IIIF manifest (digitized source)",
            "IIIF manifest (other)",
        ):
            rtype = "IIIFManifestLink"
        elif link_type in ("Digitalization", "Digitized"):
            rtype = "DigitizationLink"
        else:
            rtype = "OtherLink"

        return f"rism:{rtype}"
