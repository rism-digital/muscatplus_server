import ypres

from search_server.helpers.identifiers import (
    EXTERNAL_IDS,
    get_identifier,
    strip_prefix,
)
from search_server.helpers.solr_connection import SolrResult


class WorksSection(ypres.DictSerializer):
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:WorksSection")
    # for sources, only a single work reference is stored
    work_reference = ypres.MethodField(label="workReference")
    # for people, they can have multiple work references
    work_references = ypres.MethodField(label="workReferences")
    works_catalogues = ypres.MethodField(label="worksCatalogs")

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        # TODO: Check label
        return transl["records.work"]

    def get_works_catalogues(self, obj: SolrResult) -> dict | None:
        if "works_catalogue_json" not in obj:
            return None

        return WorksCataloguesSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    def get_work_reference(self, obj: SolrResult) -> dict | None:
        if "work_node_json" not in obj:
            return None

        work_node: dict = obj["work_node_json"]
        req = self.context["request"]
        return format_work_node(req, work_node)

    def get_work_references(self, obj: SolrResult) -> dict | None:
        if "work_nodes_json" not in obj:
            return None

        return ExternalWorkReferencesSection(
            obj, context={"request": self.context["request"]}
        ).serialized


class ExternalWorkReferencesSection(ypres.DictSerializer):
    # TODO: Add ID field and make resolvable?
    section_label = ypres.MethodField(label="sectionLabel")
    stype = ypres.StaticField(label="type", value="rism:ExternalWorkReferencesSection")
    items = ypres.MethodField(label="items")

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.external_work_reference"]

    def get_items(self, obj: SolrResult) -> list[dict]:
        work_nodes = obj["work_nodes_json"]
        req = self.context["request"]

        return [format_work_node(req, work_node) for work_node in work_nodes]


class WorksCataloguesSection(ypres.DictSerializer):
    stype = ypres.StaticField(label="type", value="rism:WorksCataloguesSection")
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_section_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        return transl["records.work_catalogs"]

    def get_items(self, obj: dict) -> list[dict]:
        work_catalogues = obj["works_catalogue_json"]
        req = self.context["request"]

        return [
            format_work_catalogue(req, work_catalogue)
            for work_catalogue in work_catalogues
        ]


def format_work_catalogue(req, work_catalogue: dict) -> dict:
    catalogue_id = strip_prefix(work_catalogue["id"])

    return {
        "id": get_identifier(
            req, "publications.publication", publication_id=catalogue_id
        ),
        "label": {"none": [work_catalogue["title"]]},
        "type": "rism:Publication",
    }


def format_work_node(req, work_node: dict) -> dict:
    transl: dict = req.ctx.translations

    work_node_title = work_node.get("work_title", "[No title]")
    work_node_composer = work_node.get("composer_name", "[No composer]")
    external_id = work_node["external_id"]
    search_url = get_identifier(
        req, "query.search", fq=f"work-node:{work_node['external_id']}"
    )

    authority, ident = external_id.split(":")
    base = EXTERNAL_IDS.get(authority, {}).get("ident")
    url = base.format(ident=ident)

    person_id = strip_prefix(work_node["composer_id"])

    return {
        "label": transl.get("records.external_work_reference"),
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
