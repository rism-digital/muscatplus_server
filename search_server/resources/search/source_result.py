import ypres

from search_server.helpers.display_fields import get_search_result_summary
from search_server.helpers.display_translators import (
    material_content_types_translator,
    material_source_types_translator,
)
from search_server.helpers.formatters import format_source_label
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.record_types import create_source_types_block
from search_server.helpers.solr_connection import SolrResult
from search_server.resources.shared.part_of import PartOfSection


class SourceSearchResult(ypres.DictSerializer):
    srid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    result_type = ypres.StaticField(label="type", value="rism:Source")
    type_label = ypres.MethodField(label="typeLabel")
    summary = ypres.MethodField()
    part_of = ypres.MethodField(label="partOf")
    flags = ypres.MethodField()

    def get_srid(self, obj: dict) -> str:
        req = self.context["request"]
        id_value: str
        # Formulate a different ID if we have an external project
        # resource.
        if "project_s" not in obj:
            id_value = strip_prefix(obj["id"])
            return get_identifier(req, "sources.source", source_id=id_value)

        project: str = obj["project_s"]
        srtype: str = obj["type"]
        id_value = strip_prefix(obj["id"])
        return get_identifier(
            req,
            "external.external",
            project=project,
            resource_type=srtype,
            ext_id=id_value,
        )

    def get_slabel(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        label: dict = format_source_label(obj["standard_titles_json"], transl)

        return label

    def get_type_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        return transl["records.source"]

    def get_summary(self, obj: dict) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        field_config: dict = {
            "source_member_composers_sm": ("sourceComposers", "records.composer", None),
            "creator_name_s": ("sourceComposer", "records.composer_author", None),
            "date_statements_sm": ("dateStatements", "records.dates", None),
            "num_source_members_i": ("numItems", "records.items_in_source", None),
            "material_source_types_sm": (
                "materialSourceTypes",
                "records.source_type",
                material_source_types_translator,
            ),
            "material_content_types_sm": (
                "materialContentTypes",
                "records.content_type",
                material_content_types_translator,
            ),
            "num_holdings_i": ("numExemplars", "records.exemplars", None),
        }
        summary: dict | None = get_search_result_summary(field_config, transl, obj)

        return summary or None

    def get_part_of(self, obj: SolrResult) -> dict | None:
        """
        Provides a pointer back to a parent. Used for Items in Sources and Incipits.
        """
        is_contents_record: bool = obj.get("is_contents_record_b", False)
        # if it isn't an item record, then it isn't part of anything!
        if not is_contents_record:
            return None

        return PartOfSection(obj, context=self.context).serialized

        # req = self.context["request"]
        # transl: dict = req.ctx.translations
        #
        # parent_title: str = obj["source_membership_title_s"]
        # parent_source_id: str = strip_prefix(obj["source_membership_id"])
        #
        # source_membership: dict = obj.get("source_membership_json", {})
        # record_type: str = source_membership.get("record_type", "item")
        # source_type: str = source_membership.get("source_type", "unspecified")
        # content_types: list[str] = source_membership.get("content_types", [])
        #
        # source_types_block: dict = create_source_types_block(
        #     record_type, source_type, content_types, transl
        # )
        #
        # return {
        #     "label": transl.get("records.item_part_of"),
        #     "source": {
        #         "id": get_identifier(req, "sources.source", source_id=parent_source_id),
        #         "type": "rism:Source",
        #         "typeLabel": transl.get("records.source"),
        #         "sourceTypes": source_types_block,
        #         "label": {"none": [parent_title]},
        #     },
        # }

    def get_flags(self, obj: dict) -> dict | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        has_digitization: bool = obj.get("has_digitization_b", False)
        is_contents_record: bool = obj.get("is_contents_record_b", False)
        # A record is collection record if it has the 'source_members_sm' key. If
        # it has the key, then it is a collection record.
        is_collection_record: bool = obj.get("source_members_sm") is not None
        has_incipits: bool = obj.get("has_incipits_b", False)
        has_iiif: bool = obj.get("has_iiif_manifest_b", False)
        linked_with_external_record: bool = obj.get("has_external_record_b", False)
        is_diamm_record: bool = obj.get("project_s") == "diamm"
        is_cantus_record: bool = obj.get("project_s") == "cantus"
        number_of_exemplars: int = obj.get("num_holdings_i", 0)
        result_flags: dict = {}

        source_type: str = obj.get("source_type_s", "unspecified")
        content_identifiers: list[str] = obj.get("content_types_sm", [])
        record_type: str = obj.get("record_type_s", "item")

        source_types_block: dict = create_source_types_block(
            record_type, source_type, content_identifiers, transl
        )

        result_flags.update(source_types_block)

        if has_digitization:
            result_flags.update({"hasDigitization": has_digitization})

        if is_contents_record:
            result_flags.update({"isContentsRecord": is_contents_record})

        if is_collection_record:
            result_flags.update({"isCollectionRecord": is_collection_record})

        if has_incipits:
            result_flags.update({"hasIncipits": has_incipits})

        if has_iiif:
            result_flags.update({"hasIIIFManifest": has_iiif})

        if number_of_exemplars > 0:
            result_flags.update({"numberOfExemplars": number_of_exemplars})

        if linked_with_external_record:
            result_flags.update(
                {"linkedWithExternalRecord": linked_with_external_record}
            )

        if is_diamm_record:
            result_flags.update({"isDIAMMRecord": is_diamm_record})

        if is_cantus_record:
            result_flags.update({"isCantusRecord": is_cantus_record})

        if is_diamm_record or is_cantus_record:
            project_url: str = obj.get("record_uri_sni", "")
            result_flags.update({"externalProjectURL": project_url})

        # return None if flags are empty.
        return result_flags or None
