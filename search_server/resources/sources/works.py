import ypres

from shared_helpers.identifiers import EXTERNAL_IDS, get_identifier
from shared_helpers.solr_connection import SolrResult


class WorksSection(ypres.AsyncDictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:WorksSection")
    work_reference = ypres.MethodField(label="workReference")

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context.get("request")
        transl: dict = req.ctx.translations

        # TODO: Check label
        return transl.get("records.work")

    def get_work_reference(self, obj: SolrResult) -> dict:
        work_node: dict = obj["work_node_json"]
        work_node_title = work_node.get("work_title", "[No title]")
        work_node_composer = work_node.get("composer_name", "[No composer]")
        external_id = work_node["external_id"]
        req = self.context.get("request")
        search_url = get_identifier(
            req, "query.search", fq=f"work-node:{work_node['external_id']}"
        )

        authority, ident = external_id.split(":")
        base = EXTERNAL_IDS.get(authority, {}).get("ident")
        url = base.format(ident=ident)

        return {
            "label": {"none": ["External work reference"]},
            "value": f"{work_node_composer}. {work_node_title}",
            "type": "rism:WorkNode",
            "search": search_url,
            "url": url,
        }
