import difflib
import logging
import re
from typing import Dict, Optional, List

import serpy
from small_asc.client import Results

from search_server.helpers.display_fields import get_display_fields, LabelConfig
from search_server.helpers.fields import StaticField
from search_server.helpers.identifiers import (
    get_identifier,
    ID_SUB
)
from search_server.helpers.serializers import ContextDictSerializer
from search_server.helpers.solr_connection import SolrResult
from search_server.helpers.vrv import render_pae
from search_server.resources.search.base_search import BaseSearchResults

log = logging.getLogger(__name__)


class SearchResults(BaseSearchResults):
    def get_modes(self, obj: Results) -> Optional[Dict]:
        req = self.context.get("request")
        cfg: Dict = req.app.ctx.config
        transl: Dict = req.app.ctx.translations

        facet_results: Optional[Dict] = obj.raw_response.get('facets')
        if not facet_results:
            return None

        mode_facet: Optional[Dict] = facet_results.get("mode")
        # if, for some reason, we don't have a mode facet we return gracefully.
        if not mode_facet:
            return None

        mode_buckets: List = mode_facet.get("buckets", [])
        mode_items: List = []
        mode_config: Dict = cfg['search']['modes']
        # Put the returned modes into a dictionary so we can look up the buckets by the key. The format is
        # {type: count}, where 'type' is the value from the Solr type field, and 'count' is the number of
        # records returned.
        mode_results: Dict = {f"{mode['val']}": mode['count'] for mode in mode_buckets}

        # This will ensure the modes are returned in the order they're listed in the configuration file. Otherwise
        #  they are returned by the order of results.
        for mode, config in mode_config.items():
            record_type = config['record_type']
            if record_type not in mode_results:
                continue

            translation_key: str = config['label']

            mode_items.append({
                "value": mode,
                "label": transl.get(translation_key),
                "count": mode_results[record_type]
            })

        return {
            "alias": "mode",
            "label": {"none": ["Result type"]},  # TODO: Translate!
            "type": "rism:ModeFacet",
            "items": mode_items
        }

    def get_items(self, obj: Results) -> Optional[List]:
        if obj.hits == 0:
            return None

        results: List[Dict] = []
        req = self.context.get('request')

        for d in obj.docs:
            if d['type'] == "source":
                results.append(SourceSearchResult(d, context={"request": req}).data)
            elif d['type'] == "person":
                results.append(PersonSearchResult(d, context={"request": req}).data)
            elif d['type'] == "institution":
                results.append(InstitutionSearchResult(d, context={"request": req}).data)
            elif d['type'] == 'place':
                results.append(PlaceSearchResult(d, context={"request": req}).data)
            elif d['type'] == "liturgical_festival":
                results.append(LiturgicalFestivalSearchResult(d, context={"request": req}).data)
            elif d['type'] == "incipit":
                results.append(IncipitSearchResult(d, context={"request": req,
                                                               "query_pae_features": self.context.get("query_pae_features")}).data)
            else:
                return None

        return results


class SourceSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Source"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    summary = serpy.MethodField()
    part_of = serpy.MethodField(
        label="partOf"
    )
    flags = serpy.MethodField()

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "sources.source", source_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        title: str = obj.get("main_title_s", "[No title]")
        #  TODO: Translate source types
        source_types: Optional[List] = obj.get("material_group_types_sm")
        shelfmark: Optional[str] = obj.get("shelfmark_s")
        siglum: Optional[str] = obj.get("siglum_s")
        num_holdings: Optional[int] = obj.get("num_holdings_i")

        label: str = title
        if source_types:
            label = f"{label}; {', '.join(source_types)}"
        if siglum and shelfmark:
            label = f"{label}; {siglum} {shelfmark}"

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations
        return transl.get("records.source")

    def get_summary(self, obj: Dict) -> Optional[List[Dict]]:
        field_config: LabelConfig = {
            "creator_name_s": ("records.composer_author", None),
        }

        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return get_display_fields(obj, transl, field_config=field_config)

    def get_part_of(self, obj: SolrResult) -> Optional[Dict]:
        """
            Provides a pointer back to a parent. Used for Items in Sources and Incipits.
        """
        is_contents_record: bool = obj.get('is_contents_record_b', False)
        # if it isn't an item record, then it isn't part of anything!
        if not is_contents_record:
            return None

        req = self.context.get("request")

        parent_title: str
        parent_source_id: str

        parent_title = obj.get("source_membership_title_s")
        parent_source_id = re.sub(ID_SUB, "", obj.get("source_membership_id"))

        transl: Dict = req.app.ctx.translations

        return {
            "label": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": get_identifier(req, "sources.source", source_id=parent_source_id),
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "label": {"none": [parent_title]}
            }
        }

    def get_flags(self, obj: Dict) -> Optional[Dict]:
        has_digitization: bool = obj.get("has_digitization_b", False)
        is_contents_record: bool = obj.get("is_contents_record_b", False)
        # A record is collection record if it has the 'source_members_sm' key. If
        # it has the key, then it is a collection record.
        is_collection_record: bool = obj.get("source_members_sm", None) is not None
        has_incipits: bool = obj.get("has_incipits_b", False)
        has_iiif: bool = obj.get("has_iiif_manifest_b", False)
        number_of_exemplars: int = obj.get("num_holdings_i", 0)
        flags: Dict = {}

        if has_digitization:
            flags.update({"hasDigitization": has_digitization})

        if is_contents_record:
            flags.update({"isContentsRecord": is_contents_record})

        if is_collection_record:
            flags.update({"isCollectionRecord": is_collection_record})

        if has_incipits:
            flags.update({"hasIncipits": has_incipits})

        if has_iiif:
            flags.update({"hasIIIFManifest": has_iiif})

        if number_of_exemplars > 0:
            flags.update({"numberOfExemplars": number_of_exemplars})

        # return None if flags are empty.
        return flags or None


class PersonSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Person"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    summary = serpy.MethodField()
    flags = serpy.MethodField()

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "people.person", person_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label: str = _format_person_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.person")

    def get_summary(self, obj: Dict) -> Optional[List[Dict]]:
        field_config = {
            "roles_sm": ("records.profession_or_function", None)
        }

        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return get_display_fields(obj, transl, field_config=field_config)

    def get_flags(self, obj: Dict) -> Optional[Dict]:
        flags: Dict = {}
        number_of_sources: int = obj.get("source_count_i", 0)

        if number_of_sources > 0:
            flags.update({"numberOfSources": number_of_sources})

        return flags or None


class InstitutionSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Institution"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    flags = serpy.MethodField()

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "institutions.institution", institution_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label = _format_institution_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.institution")

    def get_flags(self, obj: Dict) -> Optional[Dict]:
        flags: Dict = {}
        number_of_sources: int = obj.get("source_count_i", 0)

        if number_of_sources > 0:
            flags.update({"numberOfSources": number_of_sources})

        return flags or None


class PlaceSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Place"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "places.place", place_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label: str = obj.get("FIXME")

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.place")


class LiturgicalFestivalSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:LiturgicalFestival"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        id_value: str = re.sub(ID_SUB, "", obj.get("id"))

        return get_identifier(req, "festivals.festival", festival_id=id_value)

    def get_label(self, obj: Dict) -> Dict:
        label: str = obj.get("name_s")

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.liturgical_festival")


class IncipitSearchResult(ContextDictSerializer):
    srid = serpy.MethodField(
        label="id"
    )
    label = serpy.MethodField()
    result_type = StaticField(
        label="type",
        value="rism:Incipit"
    )
    type_label = serpy.MethodField(
        label="typeLabel"
    )
    part_of = serpy.MethodField(
        label="partOf"
    )
    flags = serpy.MethodField()

    def get_srid(self, obj: Dict) -> str:
        req = self.context.get('request')
        work_num: str = re.sub(ID_SUB, "", obj.get("work_num_s"))
        source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))

        return get_identifier(req, "sources.incipit", source_id=source_id, work_num=work_num)

    def get_label(self, obj: Dict) -> Dict:
        label: str = _format_incipit_label(obj)

        return {"none": [label]}

    def get_type_label(self, obj: Dict) -> Dict:
        req = self.context.get("request")
        transl = req.app.ctx.translations

        return transl.get("records.incipit")

    def get_part_of(self, obj: SolrResult) -> Optional[Dict]:
        """
            Provides a pointer back to the parent for this incipit
        """
        req = self.context.get("request")
        parent_title: str
        parent_source_id: str

        parent_title: str = obj.get("source_title_s")
        parent_source_id: str = re.sub(ID_SUB, "", obj.get("source_id"))
        transl: Dict = req.app.ctx.translations

        return {
            "label": transl.get("records.item_part_of"),
            "type": "rism:PartOfSection",
            "source": {
                "id": get_identifier(req, "sources.source", source_id=parent_source_id),
                "type": "rism:Source",
                "typeLabel": transl.get("records.source"),
                "label": {"none": [parent_title]}
            }
        }

    def get_flags(self, obj: SolrResult) -> Optional[dict]:
        if not obj.get("music_incipit_s"):
            log.debug("No music incipit")
            return None

        req = self.context.get("request")

        # Grab the PAE features we computed from the incoming query request. These will
        # be used to perform the highlighting
        query_pae_features: Optional[dict] = self.context.get("query_pae_features")
        if not query_pae_features:
            svg, midi = _render_without_highlighting(req, obj)
        else:
            svg, midi = _render_with_highlighting(req, obj, query_pae_features)

        return {
            "highlightedResult": [{
                    "format": "image/svg+xml",
                    "data": svg
                }, {
                    "format": "audio/midi",
                    "data": midi
                }]
        }


def _format_institution_label(obj: Dict) -> str:
    city = siglum = ""

    if 'city_s' in obj:
        city = f", {obj['city_s']}"
    if 'siglum_s' in obj:
        siglum = f" ({obj['siglum_s']})"

    return f"{obj['name_s']}{city}{siglum}"


def _format_person_label(obj: Dict) -> str:
    name: str = obj.get("name_s")
    dates: str = f" ({d})" if (d := obj.get("date_statement_s")) else ""

    return f"{name}{dates}"


def _format_incipit_label(obj: Dict) -> str:
    """
    The format for incipit titles is:

    Source title: Work num (supplied title)

    e.g., "Overtures - winds, stck: 1.1.1 (Allegro)"

    If the supplied title is not on the record, it will be omitted.

    :param obj: A Solr result object containing an incipit record
    :return: A string of the composite title
    """
    work_num: str = obj['work_num_s']
    source_title: str = obj["source_title_s"]
    title: str = f" ({d})" if (d := obj.get("title_s")) else ""

    return f"{source_title}: {work_num}{title}"


def _render_incipit_pae(obj: SolrResult) -> Optional[tuple]:
    pae_code: Optional[str] = obj.get("original_pae_sni")

    if not pae_code:
        log.debug("no PAE code")
        return None

    rendered_pae: Optional[tuple] = render_pae(pae_code, use_crc=True)

    if not rendered_pae:
        log.error("Could not load music incipit for %s", obj.get("id"))
        return None

    return rendered_pae


def _render_without_highlighting(req, obj: SolrResult) -> Optional[tuple]:
    rendered_incipit: Optional[tuple] = _render_incipit_pae(obj)

    if not rendered_incipit:
        return None

    return rendered_incipit


def _render_with_highlighting(req, obj: SolrResult, query_pae_features: Optional[dict]) -> Optional[tuple]:
    if not query_pae_features:
        log.error("Could not highlight a search result without query features!")
        return None

    svg, b64midi = _render_incipit_pae(obj)

    # For now, we only highlight interval successions.
    document_interval_features: list = [str(s) for s in obj["intervals_im"]]
    document_interval_ids: list = obj["interval_ids_json"]

    query_interval_feature: list = query_pae_features["intervals"]

    log.debug("Document features: %s", document_interval_features)
    log.debug("Query features: %s", query_interval_feature)

    # Run the query features and the document features through a longest contiguous matching subsequence matcher.
    smtch = difflib.SequenceMatcher(a=query_interval_feature, b=document_interval_features)
    all_blks: list = smtch.get_matching_blocks()

    # The last block is always a 'dummy' so we throw it away.
    used_blks: list = all_blks[:-1]

    ids_to_highlight = []
    for blk in used_blks:
        seq = document_interval_ids[blk.b:blk.b + blk.size]
        ids_to_highlight.extend(seq)

    log.debug("IDs to highlight: %s", ids_to_highlight)

    highlight_stmts = []
    for noteids in ids_to_highlight:
        highlight_stmts.append(
            f"g[data-id=\"{noteids[0]}\"] {{ fill: red; }} g[data-id=\"{noteids[1]}\"] {{ fill: red; }}"
        )
    highlight_css_stmt = " ".join(highlight_stmts)

    # Use Regex to insert the highlighting. The other option is to read the SVG in as XML and
    # manipulate the DOM, which would be more correct, but probably slower for such a simple replacement.
    highlighted_svg: str = re.sub(r'<style type="text\/css">(?P<existing_style>.*)</style>', rf'<style type="text/css">\1 {highlight_css_stmt}</style>', svg)

    return highlighted_svg, b64midi
