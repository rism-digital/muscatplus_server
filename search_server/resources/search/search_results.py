import difflib
import logging
import re

import ypres
from small_asc.client import Results

from search_server.helpers.display_fields import get_search_result_summary
from search_server.helpers.display_translators import (
    gnd_country_code_labels_translator,
    key_mode_value_translator,
    material_content_types_translator,
    material_source_types_translator,
    title_json_value_translator,
)
from search_server.helpers.formatters import (
    format_incipit_label,
    format_institution_label,
    format_person_label,
    format_source_label,
)
from search_server.helpers.identifiers import (
    get_identifier,
    strip_prefix,
)
from search_server.helpers.record_types import create_source_types_block
from search_server.helpers.search_request import IncipitModeValues
from search_server.helpers.solr_connection import SolrConnection, SolrResult
from search_server.helpers.vrv import RenderedIncipit, render_pae
from search_server.resources.search.base_search import BaseSearchResults

log = logging.getLogger("mp_server")


CSS_REPLACEMENT_PATTERN: re.Pattern = re.compile(
    r'<style type="text/css">(?P<existing_style>.*)</style>'
)


class SearchResults(BaseSearchResults):
    query_validation = ypres.MethodField(label="queryValidation")

    def get_query_validation(self, obj: Results) -> dict | None:
        if "query_validation" not in self.context:
            return None

        return self.context["query_validation"]

    def get_modes(self, obj: Results) -> dict | None:
        is_probe: bool = self.context.get("probe_request", False)
        if is_probe:
            return None

        facet_results: dict | None = obj.raw_response.get("facets")
        if not facet_results:
            return None

        mode_facet: dict | None = facet_results.get("mode")
        # if, for some reason, we don't have a mode facet we return gracefully.
        if not mode_facet:
            return None

        mode_buckets: list = mode_facet.get("buckets", [])
        # if there are no buckets for this mode, then we shouldn't return the
        # mode facet block at all.
        if len(mode_buckets) == 0:
            return None

        req = self.context["request"]
        cfg: dict = req.app.ctx.config
        transl: dict = req.app.ctx.translations

        mode_items: list = []
        mode_config: dict = cfg["search"]["modes"]
        # Put the returned modes into a dictionary so we can look up the buckets by the key. The format is
        # {type: count}, where 'type' is the value from the Solr type field, and 'count' is the number of
        # records returned.
        mode_results: dict = {f"{mode['val']}": mode["count"] for mode in mode_buckets}

        # This will ensure the modes are returned in the order they're listed in the configuration file. Otherwise
        #  they are returned by the order of results.
        for mode, config in mode_config.items():
            record_type = config["record_type"]
            if record_type not in mode_results:
                continue

            translation_key: str = config["label"]

            mode_items.append(
                {
                    "value": mode,
                    "label": transl.get(translation_key),
                    "count": mode_results[record_type],
                }
            )

        return {
            "alias": "mode",
            "label": {"none": ["Result type"]},  # TODO: Translate!
            "type": "rism:ModeFacet",
            "items": mode_items,
        }

    async def get_items(self, obj: Results) -> list | None:
        is_probe: bool = self.context.get("probe_request", False)
        # If we have no hits, or we have a 'probe' request, then don't
        # return an empty items block.
        if obj.hits == 0 or is_probe:
            return None

        results: list[dict] = []
        req = self.context["request"]
        is_composite: bool = self.context.get("is_composite", False)

        for d in obj.docs:
            dtype: str = d["type"]

            match dtype:
                case "source":
                    results.append(
                        SourceSearchResult(d, context={"request": req}).serialized
                    )
                case "person":
                    results.append(
                        PersonSearchResult(d, context={"request": req}).serialized
                    )
                case "institution":
                    results.append(
                        InstitutionSearchResult(d, context={"request": req}).serialized
                    )
                case "incipit":
                    results.append(
                        IncipitSearchResult(
                            d,
                            context={
                                "request": req,
                                "query_pae_features": self.context.get(
                                    "query_pae_features"
                                ),
                            },
                        ).serialized
                    )
                case "holding" if is_composite is True:
                    # The SLOW path, but there shouldn't be many of these, so hopefully it won't be too bad.
                    # Look up the source based on the ID from the holding, then fetch the doc. This means this will
                    # trigger a Solr lookup for every result in the list that is a holding, but this should only ever
                    # happen when a source is marked as composite, and the relationship to an item in the source is
                    # a holding record.
                    source_id: str = d["source_id"]
                    source_doc: dict | None = await SolrConnection.get(source_id)  # type: ignore
                    if not source_doc:
                        log.error("Malformed holding %s", d["id"])
                        continue

                    results.append(
                        SourceSearchResult(
                            source_doc, context={"request": req}
                        ).serialized
                    )
                case _:
                    continue

        return results


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

        req = self.context["request"]
        transl: dict = req.ctx.translations

        parent_title: str = obj["source_membership_title_s"]
        parent_source_id: str = strip_prefix(obj["source_membership_id"])

        source_membership: dict = obj.get("source_membership_json", {})
        record_type: str = source_membership.get("record_type", "item")
        source_type: str = source_membership.get("source_type", "unspecified")
        content_types: list[str] = source_membership.get("content_types", [])

        source_types_block: dict = create_source_types_block(
            record_type, source_type, content_types, transl
        )

        return {
            "label": transl.get("records.item_part_of"),
            "source": {
                "id": get_identifier(req, "sources.source", source_id=parent_source_id),
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "sourceTypes": source_types_block,
                "label": {"none": [parent_title]},
            },
        }

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


class PersonSearchResult(ypres.DictSerializer):
    srid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    result_type = ypres.StaticField(label="type", value="rism:Person")
    type_label = ypres.MethodField(label="typeLabel")
    summary = ypres.MethodField()
    flags = ypres.MethodField()

    def get_srid(self, obj: dict) -> str:
        req = self.context["request"]

        id_value: str
        if "project_s" not in obj:
            id_value = strip_prefix(obj["id"])
            return get_identifier(req, "people.person", person_id=id_value)

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
        label: str = format_person_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.person"]

    def get_summary(self, obj: dict) -> dict | None:
        field_config = {
            "profession_function_sm": ("roles", "records.profession_or_function", None),
            "total_sources_i": ("numSources", "records.sources", None),
            "gender_s": ("gender", "records.gender", None),
        }

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_search_result_summary(field_config, transl, obj)

    def get_flags(self, obj: dict) -> dict | None:
        result_flags: dict = {}
        number_of_sources: int = obj.get("source_count_i", 0)
        linked_with_external_record: bool = obj.get("has_external_record_b", False)
        is_diamm_record: bool = obj.get("project_s") == "diamm"
        is_cantus_record: bool = obj.get("project_s") == "cantus"

        if number_of_sources > 0:
            result_flags.update({"numberOfSources": number_of_sources})

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

        return result_flags or None


class InstitutionSearchResult(ypres.DictSerializer):
    srid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    result_type = ypres.StaticField(label="type", value="rism:Institution")
    type_label = ypres.MethodField(label="typeLabel")
    summary = ypres.MethodField()
    flags = ypres.MethodField()

    def get_srid(self, obj: dict) -> str:
        req = self.context["request"]

        id_value: str
        if "project_s" not in obj:
            id_value = strip_prefix(obj["id"])
            return get_identifier(
                req, "institutions.institution", institution_id=id_value
            )

        project: str = obj["project_s"]
        srtype = obj["project_type_s"] if "project_type_s" in obj else obj["type"]
        id_value = strip_prefix(obj["id"])

        return get_identifier(
            req,
            "external.external",
            project=project,
            resource_type=srtype,
            ext_id=id_value,
        )

    def get_slabel(self, obj: dict) -> dict:
        label = format_institution_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl = req.ctx.translations

        return transl.get("records.institution")

    def get_summary(self, obj: dict) -> dict | None:
        field_config: dict = {
            "gnd_country_codes_sm": (
                "countryName",
                "records.country",
                gnd_country_code_labels_translator,
            ),
            "alternate_names_sm": ("otherNames", "records.other_form_of_name", None),
            "total_sources_i": (
                "totalSources",
                "records.sources",
                None,
            ),  # TODO: Find a better label
        }

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_search_result_summary(field_config, transl, obj)

    def get_flags(self, obj: dict) -> dict | None:
        result_flags: dict = {}
        number_of_sources: int = obj.get("total_sources_i", 0)
        linked_with_external_record: bool = obj.get("has_external_record_b", False)
        is_diamm_record: bool = obj.get("project_s") == "diamm"
        is_cantus_record: bool = obj.get("project_s") == "cantus"

        if number_of_sources > 0:
            result_flags.update({"numberOfSources": number_of_sources})

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

        return result_flags or None


class IncipitSearchResult(ypres.DictSerializer):
    srid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    result_type = ypres.StaticField(label="type", value="rism:Incipit")
    type_label = ypres.MethodField(label="typeLabel")
    part_of = ypres.MethodField(label="partOf")
    summary = ypres.MethodField()
    rendered = ypres.MethodField()
    score = ypres.MethodField()

    def get_srid(self, obj: dict) -> str:
        req = self.context["request"]
        work_num: str = strip_prefix(obj["work_num_s"])
        source_id: str = strip_prefix(obj["source_id"])

        return get_identifier(
            req, "sources.incipit", source_id=source_id, work_num=work_num
        )

    def get_slabel(self, obj: dict) -> dict:
        incipit_label: str = format_incipit_label(obj)
        return {"none": [incipit_label]}

    def get_type_label(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        return transl["records.incipit"]

    def get_summary(self, obj: dict) -> dict | None:
        field_config: dict = {
            "creator_name_s": ("incipitComposer", "records.composer_author", None),
            "standard_titles_json": (
                "sourceTitle",
                "records.source",
                title_json_value_translator,
            ),
            "text_incipit_sm": ("textIncipit", "records.text_incipit", None),
            "voice_instrument_s": ("voiceInstrument", "records.voice_instrument", None),
            "original_pae_sni": ("paeCode", "records.plaine_and_easie", None),
        }

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_search_result_summary(field_config, transl, obj)

    def get_part_of(self, obj: SolrResult) -> dict | None:
        """
        Provides a pointer back to the parent for this incipit
        """
        req = self.context["request"]
        parent_title: str = obj["main_title_s"]
        parent_source_id: str = strip_prefix(obj["source_id"])
        transl: dict = req.ctx.translations

        record_type: str = obj.get("record_type_s", "item")
        source_type: str = obj.get("source_type_s", "unspecified")
        content_types: list[str] = obj.get("content_types_sm", [])

        source_types_block: dict = create_source_types_block(
            record_type, source_type, content_types, transl
        )

        return {
            "sectionLabel": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": get_identifier(req, "sources.source", source_id=parent_source_id),
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "sourceTypes": source_types_block,
                "label": {"none": [parent_title]},
            },
        }

    def get_rendered(self, obj: SolrResult) -> list | None:
        if not obj.get("has_notation_b", False):
            log.debug("No music incipit")
            return None

        req = self.context["request"]

        # Grab the PAE features we computed from the incoming query request. These will
        # be used to perform the highlighting
        query_pae_features: dict | None = self.context.get("query_pae_features")

        if not query_pae_features:
            svg, midi = _render_incipit_pae(obj)
        else:
            # Find out what mode we're operating in to determine which fields we're using.
            search_mode: str = req.args.get("im", IncipitModeValues.INTERVALS)
            svg, midi = _render_with_highlighting(obj, query_pae_features, search_mode)

        if not svg:
            return None

        return [
            {"format": "image/svg+xml", "data": svg},
            {"format": "audio/midi", "data": midi},
        ]

    def get_score(self, obj: SolrResult) -> float | None:
        return obj.get("custom_score")


def _render_incipit_pae(obj: dict) -> RenderedIncipit:
    pae_code: str | None = obj.get("original_pae_sni")

    if not pae_code:
        log.debug("no PAE code")
        return None, None

    is_mensural: bool = obj.get("is_mensural_b", False)
    rendered_pae: RenderedIncipit = render_pae(
        pae_code, use_crc=True, is_mensural=is_mensural
    )

    if not rendered_pae[0]:
        log.error("Could not load music incipit for %s", obj.get("id"))
        return None, None

    return rendered_pae


def _render_with_highlighting(
    obj: SolrResult, query_pae_features: dict | None, search_mode: str
) -> RenderedIncipit:
    if not query_pae_features:
        log.error("Could not highlight a search result without query features!")
        return None, None

    svg, b64midi = _render_incipit_pae(obj)
    if not svg:
        return None, None

    mode_fields = {
        IncipitModeValues.EXACT_PITCHES: (
            "pitches_sm",
            "pitches_ids_json",
            "pitchesChromatic",
        ),
        IncipitModeValues.CONTOUR: (
            "contour_refined_sm",
            "interval_ids_json",
            "intervalRefinedContour",
        ),
    }
    feature_field, ids_field, query_features_field = mode_fields.get(
        search_mode, ("intervals_im", "interval_ids_json", "intervalsChromatic")
    )

    if feature_field not in obj:
        return svg, b64midi

    document_interval_features: list = list(map(str, obj[feature_field]))
    document_interval_ids: list = obj[ids_field]
    query_interval_feature: list = query_pae_features[query_features_field]

    log.debug("Document features: %s", document_interval_features)
    log.debug("Query features: %s", query_interval_feature)

    smtch = difflib.SequenceMatcher(
        a=query_interval_feature, b=document_interval_features
    )
    used_blks = smtch.get_matching_blocks()[:-1]

    highlight_ids = {
        nid
        for blk in used_blks
        for noteids in document_interval_ids[blk.b : blk.b + blk.size]
        for nid in noteids
    }

    if not highlight_ids:
        return svg, b64midi

    highlight_css_stmt = " ".join(
        f'g[data-id="{nid}"] {{ fill: red; color: red; }}' for nid in highlight_ids
    )

    highlighted_svg = re.sub(
        CSS_REPLACEMENT_PATTERN,
        rf'<style type="text/css">\1 {highlight_css_stmt}</style>',
        svg,
    )

    return highlighted_svg, b64midi


class WorkSearchResult(ypres.DictSerializer):
    srid = ypres.MethodField(label="id")
    slabel = ypres.MethodField(label="label")
    result_type = ypres.StaticField(label="type", value="rism:Work")
    type_label = ypres.MethodField(label="typeLabel")
    part_of = ypres.MethodField(label="partOf")
    summary = ypres.MethodField()
    flags = ypres.MethodField()
    rendered = ypres.MethodField()

    def get_srid(self, obj: SolrResult) -> str:
        req = self.context["request"]
        work_id = obj["rism_id"]
        return get_identifier(req, "works.work", work_id=work_id)

    def get_slabel(self, obj: SolrResult) -> dict:
        return {"none": [f"{obj['standard_title_s']}"]}

    def get_type_label(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl = req.ctx.translations

        return transl.get("records.work")

    def get_part_of(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        wcg: dict = obj["works_catalogue_json"]

        catalogue_id: str = strip_prefix(wcg["id"])
        parent_title: str = wcg["formatted"]

        return {
            "label": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "publication": {
                "id": get_identifier(
                    req, "publications.publication", publication_id=catalogue_id
                ),
                "type": "rism:Publication",
                "typeLabel": transl.get("records.work_catalog"),
                "label": {"none": [parent_title]},
            },
        }

    def get_summary(self, obj: SolrResult) -> dict | None:
        field_config: dict = {
            "key_mode_s": ("keyMode", "records.key_or_mode", key_mode_value_translator),
            "text_incipit_sm": ("textIncipit", "records.text_incipit", None),
        }

        req = self.context["request"]
        transl: dict = req.ctx.translations

        return get_search_result_summary(field_config, transl, obj)

    def get_flags(self, obj: SolrResult) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        flags: dict = {}

        catalogue_code = obj.get("catalogue_s")
        catalogue_number = obj.get("number_page_s")
        if catalogue_code and catalogue_number:
            flags["catalogNumber"] = f"{catalogue_code} {catalogue_number}"

        number_of_sources: int = obj.get("source_count_i", 0)
        flags.update({"numberOfSources": number_of_sources})

        key_mode: str | None = obj.get("key_mode_s")
        if key_mode:
            key_mode_vals = key_mode_value_translator(key_mode, transl)
            flags["keyMode"] = key_mode_vals

        scoring: list[str] | None = obj.get("scoring_summary_sm")
        if scoring:
            flags["scoringSummary"] = "; ".join(scoring)

        return flags

    def get_rendered(self, obj: SolrResult) -> dict | None:
        if not obj.get("has_notation_b", False):
            return None

        svg, _ = _render_incipit_pae(obj)

        if not svg:
            return None

        return {"format": "image/svg+xml", "data": svg}
