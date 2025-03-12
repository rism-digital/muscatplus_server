import re

import ypres

from shared_helpers.identifiers import EXTERNAL_IDS, ID_SUB, get_identifier
from shared_helpers.solr_connection import SolrResult


class WorksSection(ypres.AsyncDictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:WorksSection")
    # for sources, only a single work reference is stored
    work_reference = ypres.MethodField(label="workReference")
    # for people, they can have multiple work references
    work_references = ypres.MethodField(label="workReferences")

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        # TODO: Check label
        return transl.get("records.work")

    def get_work_reference(self, obj: SolrResult) -> dict | None:
        if "work_node_json" not in obj:
            return None

        work_node: dict = obj["work_node_json"]
        req = self.context.get("request")
        return format_work_node(req, work_node)

    async def get_work_references(self, obj: SolrResult) -> dict | None:
        if "work_nodes_json" not in obj:
            return None

        return await ExternalWorkReferencesSection(
            obj, context={"request": self.context.get("request")}
        ).data


class ExternalWorkReferencesSection(ypres.AsyncDictSerializer):
    # TODO: Add ID field and make resolvable?
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:ExternalWorkReferencesSection")
    items = ypres.MethodField(label="items")

    def get_section_label(self, obj: SolrResult) -> dict:
        # TODO: Translations!
        return {"none": ["External work references"]}

    def get_items(self, obj: SolrResult) -> list[dict]:
        work_nodes = obj["work_nodes_json"]
        req = self.context.get("request")

        return [format_work_node(req, work_node) for work_node in work_nodes]


def format_work_node(req, work_node: dict) -> dict:
    work_node_title = work_node.get("work_title", "[No title]")
    work_node_composer = work_node.get("composer_name", "[No composer]")
    external_id = work_node["external_id"]
    search_url = get_identifier(
        req, "query.search", fq=f"work-node:{work_node['external_id']}"
    )

    authority, ident = external_id.split(":")
    base = EXTERNAL_IDS.get(authority, {}).get("ident")
    url = base.format(ident=ident)

    person_id = re.sub(ID_SUB, "", work_node["composer_id"])

    return {
        "label": {"none": ["External work reference"]},
        "relatedTo": {
            "id": get_identifier(req, "people.person", person_id=person_id),
            "label": {"none": [work_node_composer]},
            "type": "rism:Person",
        },
        "value": f"{work_node_title}",
        "type": "rism:WorkNode",
        "search": search_url,
        "url": url,
        "externalIdentifier": external_id,
        "sourceCount": work_node.get("source_count", 1),
    }
