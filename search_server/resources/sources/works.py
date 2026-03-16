import ypres

from search_server.helpers.display_translators import (
    compile_publication_info,
    format_publication_info,
    title_json_value_translator,
)
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
    works = ypres.MethodField()
    # for people, they can have multiple work references
    work_references = ypres.MethodField(label="workReferences")
    works_catalogues = ypres.MethodField(label="worksCatalogs")

    def get_section_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        # TODO: Check label
        return transl["records.work"]

    def get_works(self, obj: SolrResult) -> dict | None:
        if "works_json" not in obj:
            return None

        # For sources
        return WorksListSection(
            obj, context={"request": self.context["request"]}
        ).serialized

    # Works catalogues in sources are for showing in the bibliography section in sources.
    # So we will skip rendering it in this section if it is present on a source.
    # For people it is valid.
    def get_works_catalogues(self, obj: SolrResult) -> dict | None:
        if obj["type"] == "source" or "works_catalogue_json" not in obj:
            return None

        return WorksCatalogueSection(
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


class WorksCatalogueSection(ypres.DictSerializer):
    stype = ypres.StaticField(label="type", value="rism:WorksCataloguesSection")
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_section_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        return transl["records.work_catalogs"]

    def get_items(self, obj: dict) -> list[dict]:
        req = self.context["request"]
        transl = req.ctx.translations

        out = []
        for v in obj["works_catalogue_json"]:
            _, prepped_entry = compile_publication_info(v)
            formatted_entry = format_publication_info(prepped_entry)
            publication_id = strip_prefix(v["id"])
            d = {
                "label": transl["records.catalog_works"],
                "value": {"none": [formatted_entry]},
                "relatedTo": {
                    "id": get_identifier(
                        req, "publications.publication", publication_id=publication_id
                    ),
                    "label": {"none": ["View Work Catalog on RISM Online"]},
                    "type": "rism:Publication",
                    "status": v.get("status"),
                },
            }
            out.append(d)

        return out


class WorksListSection(ypres.DictSerializer):
    stype = ypres.StaticField(label="type", value="rism:WorksCataloguesSection")
    section_label = ypres.MethodField(label="sectionLabel")
    items = ypres.MethodField()

    def get_section_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        return transl["records.work_catalogs"]

    def get_items(self, obj: dict) -> list[dict]:
        work_catalogues = obj["works_json"]
        req = self.context["request"]

        return [
            format_work_entry(req, work_catalogue) for work_catalogue in work_catalogues
        ]


def format_work_label(obj: dict) -> str:
    title: str = obj.get("title", "")
    catalogue: str = f" {obj.get('catalogue', '')}"
    catalogue_num: str = f" {obj.get('number_page', '')}"

    return f"{title} {catalogue}{catalogue_num}"


def format_work_entry(req, work_entry: dict) -> dict:
    transl = req.ctx.translations
    work_id = strip_prefix(work_entry["id"])

    return {
        "id": get_identifier(req, "works.work", work_id=work_id),
        "label": title_json_value_translator([work_entry], transl),
        "type": "rism:Work",
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
