import re
from typing import Optional

from search_server.helpers.identifiers import ID_SUB
from search_server.helpers.languages import SUPPORTED_LANGUAGES

_SOURCE_TYPE_LABEL_MAP: dict = {
    "printed": "",
    "manuscript": "",
    "composite": "",
    "unspecified": ""
}

_RECORD_TYPE_LABEL_MAP: dict = {
    "item": "",
    "collection": "",
    "composite": ""
}

_CONTENT_TYPE_LABEL_MAP: dict = {
    "libretto": "",
    "treatise": "",
    "musical": "",
    "composite_content": ""
}

_MATERIAL_GROUP_TYPES_MAP: dict = {
    "Print": "",
    "Autograph manuscript": "",
    "Libretto, handwritten": "",
    "Libretto, printed": "",
    "Manuscript copy": "",
    "Manuscript copy with autograph annotations": "",
    "Other": "",
    "Partial autograph": "",
    "Possible autograph manuscript": "",
    "Print with autograph annotations": "",
    "Print with non-autograph annotations": "",
    "Treatise, handwritten": "",
    "Treatise, printed": ""
}

_KEY_MODE_MAP: dict = {
    "A": "records.a_major",
    "a": "records.a_minor",
    "A|b": "records.af_major",
    "a|b": "records.af_minor",
    "A|x": "records.as_major",
    "a|x": "records.as_minor",
    "B": "records.b_major",
    "b": "records.b_minor",
    "B|b": "records.bf_major",
    "b|b": "records.bf_minor",
    "C": "records.c_major",
    "c": "records.c_minor",
    "C|b": "records.cf_major",
    "c|b": "records.cf_minor",
    "C|x": "records.cs_major",
    "c|x": "records.cs_minor",
    "D": "records.d_major",
    "d": "records.d_minor",
    "D|b": "records.df_major",
    "d|b": "records.df_minor",
    "D|x": "records.ds_major",
    "d|x": "records.ds_minor",
    "E": "records.e_major",
    "e": "records.e_minor",
    "E|b": "records.ef_major",
    "e|b": "records.ef_minor",
    "F": "records.f_major",
    "f": "records.f_minor",
    "F|x": "records.fs_major",
    "f|x": "records.fs_minor",
    "G": "records.g_major",
    "g": "records.g_minor",
    "G|b": "records.gf_major",
    "g|b": "records.gf_minor",
    "G|x": "records.gs_major",
    "g|x": "records.gs_minor",
    "1t": "records.mode_1t",
    "1tt": "records.mode_1tt",
    "2t": "records.mode_2t",
    "2tt": "records.mode_2tt",
    "3t": "records.mode_3t",
    "3tt": "records.mode_3tt",
    "4t": "records.mode_4t",
    "4tt": "records.mode_4tt",
    "5t": "records.mode_5t",
    "5tt": "records.mode_5tt",
    "6t": "records.mode_6t",
    "6tt": "records.mode_6tt",
    "7t": "records.mode_7t",
    "7tt": "records.mode_7tt",
    "8t": "records.mode_8t",
    "8tt": "records.mode_8tt",
    "9t": "records.mode_9t",
    "9tt": "records.mode_9tt",
    "10t": "records.mode_10t",
    "10tt": "records.mode_10tt",
    "11t": "records.mode_11t",
    "11tt": "records.mode_11tt",
    "12t": "records.mode_12t",
    "12tt": "records.mode_12tt",
    "1byz": "records.octoechos1",
    "2byz": "records.octoechos2",
    "3byz": "records.octoechos3",
    "4byz": "records.octoechos4",
    "5byz": "records.octoechos5",
    "6byz": "records.octoechos6",
    "7byz": "records.octoechos7",
    "8byz": "records.octoechos8",
}
_CLEF_MAP: dict = {
    "G-2": "records.g_minus_2_treble",
    "C-1": "records.c_minus_1"
}
_SUBHEADING_MAP: dict = {
    "Excerpts": "records.excerpts",
    "Sketches": "records.sketches",
    "Fragments": "records.fragments",
    "Inserts": "records.inserts"
}
_ARRANGEMENT_MAP: dict = {
    "Arr": "records.arrangement",
    "arr": "records.arrangement",
    "Arrangement": "records.arrangement"
}

_PRINTING_TECHNIQUE_MAP: dict = {
    "Autography": "records.autography",
    "Computer printout": "records.computer_printout",
    "Engraving": "records.engraving",
    "Facsimile": "records.facsimile",
    "Lithography": "records.lithography",
    "Offset printing": None,  # TODO: Needs a translation
    "Photoreproductive process": "records.photoreproductive_process",
    "Reproduction": "records.reproduction",
    "Transparency": "records.transparency",
    "Typescript": "records.typescript",
    "Typography": "records.typography",
    "Woodcut": "records.woodcut",
}

_QUALIFIER_LABELS_MAP = {
    None: "records.unknown",
    "Ascertained": "records.ascertained",
    "Verified": "records.verified",
    "Conjectural": "records.conjectural",
    "Alleged": "records.alleged",
    "Doubtful": "records.doubtful",
    "Misattributed": "records.misattributed"
}

_PERSON_INSTITUTION_RELATIONSHIP_LABELS_MAP = {
    None: "records.unknown",
    "brother of": "records.brother_of",
    "child of": "records.child_of",
    "confused with": "records.confused_with",
    "father of": "records.father_of",
    "married to": "records.married_to",
    "mother of": "records.mother_of",
    "other": "records.other",
    "related to": "records.related_to",
    "sister of": "records.sister_of",
    "arr": "records.arranger",
    "asg": "records.assignee",
    "asn": "records.associated_name",
    "aut": "records.author",
    "bsl": "records.bookseller",
    "ccp": "records.conceptor",
    "cmp": "records.composer",
    "cns": "records.censor",
    "cph": "records.copyright_holder",
    "cre": "records.composer_author",  # A special case, where the cre relator code is used to label the 100 main entry field.
    "ctb": "records.contributor",
    "dpt": "records.depositor",
    "dst": "records.distributor",
    "dte": "records.dedicatee",
    "edt": "records.editor",
    "egr": "records.engraver",
    "evp": "records.event_place",
    "fmo": "records.former_owner",
    "ill": "records.illustrator",
    "lbt": "records.librettist",
    "lse": "records.licensee",
    "ltg": "records.lithographer",
    "lyr": "records.lyricist",
    "oth": "records.other",
    "pbl": "records.publisher",
    "ppm": "records.papermaker",
    "prf": "records.performer",
    "prt": "records.printer",
    "scr": "records.copyist",
    "trl": "records.translator",
    "tyd": "records.type_designer"
}

_PLACE_RELATIONSHIP_LABELS_MAP = {
    None: "records.unknown",
    "go": "records.place_birth",
    "ha": "records.place_origin",
    "so": "records.place_death",
    "wl": "records.country_active",
    "wo": "records.place_active",
    "wr": "records.region_active",
}

_PERSON_NAME_VARIANT_TYPES_MAP = {
    None: "records.unknown",
    "bn": "records.nickname",
    "da": "records.pseudonym",
    "do": "records.religious_name",
    "ee": "records.married_name",
    "gg": "records.birth_name",
    "in": "records.initials",
    "tn": "records.baptismal_name",
    "ub": "records.translation",
    "xx": "records.uncategorized",
    "z": "records.alternate_spelling"
}

SIGLA_COUNTRY_MAP = {
    "A": "places.austria",
    "AND": "places.andorra",
    "AUS": "places.australia",
    "B": "places.belgium",
    "BOL": "places.bolivia",
    "BR": "places.brazil",
    "BY": "places.belarus",
    "CDN": "places.canada",
    "CH": "places.switzerland",
    "CN": "places.china",
    "CO": "places.colombia",
    "CZ": "places.czech_republic",
    "D": "places.german",
    "DK": "places.denmark",
    "E": "places.spain",
    "EV": "places.estonia",
    "F": "places.france",
    "FIN": "places.finland",
    "GB": "places.uk",
    "GCA": "places.guatemala",
    "GR": "places.greece",
    "H": "places.hungary",
    "HK": "places.hong_kong",
    "HR": "places.croatia",
    "I": "places.italy",
    "IL": "places.israel",
    "IRL": "places.ireland",
    "J": "places.japan",
    "LT": "places.lithuania",
    "LV": "places.latvia",
    "M": "places.malta",
    "MEX": "places.mexico",
    "N": "places.norway",
    "NL": "places.netherlands",
    "NZ": "places.new_zealand",
    "P": "places.portugal",
    "PE": "places.peru",
    "PL": "places.poland",
    "RA": "places.argentina",
    "RC": "places.taiwan",
    "RCH": "places.chile",
    "RO": "places.romania",
    "ROK": "places.korea",
    "ROU": "places.uruguay",
    "RP": "places.philippines",
    "RUS": "places.russian_federation",
    "S": "places.sweden",
    "SI": "places.slovenia",
    "SK": "places.slovakia",
    "UA": "places.ukraine",
    "US": "places.usa",
    "V": "places.holy_see",
    "VE": "places.venezuela",
    "XX": "records.unknown",
}


def __lookup_translations(value, available_translations: dict, translations_map: dict) -> dict:
    """
    Returns a translated value from the Solr records. The available translations are
    all the translated keys in their respective languages; the translations map
    is the mapping between the value stored in Solr, and the key in the translation.

    If for some reason the value is not found in the map, it is returned with a
    language code of "none" to indicate that it is a literal reflection of the value,
    and not a translated value.

    :param value: A key or mode value from the Solr index
    :param available_translations: A dictionary of available translations
    :param translations_map: A dictionary mapping Solr values to the key in the available translations.
    :return: A dictionary corresponding to a language map for that value.
    """
    trans_key: Optional[str] = translations_map.get(value)
    if not trans_key:
        return {"none": [value]}
    return available_translations.get(trans_key)


def country_code_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, SIGLA_COUNTRY_MAP)


def person_name_variant_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _PERSON_NAME_VARIANT_TYPES_MAP)


def place_relationship_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _PLACE_RELATIONSHIP_LABELS_MAP)


def qualifier_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _QUALIFIER_LABELS_MAP)


def person_institution_relationship_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _PERSON_INSTITUTION_RELATIONSHIP_LABELS_MAP)


def printing_techniques_translator(values: list, translations: dict) -> dict:
    """
    Translates the printing techniques values. Since the values can be a list of
    printing techniques, we need to gather all possible printing techniques and return
    them.

    :param values: A list of values to translate
    :param translations: The source of all translations
    :return: A dictionary of translated terms.
    """
    result: dict = {k: [] for k in SUPPORTED_LANGUAGES}
    for technique in values:
        transl_key: Optional[str] = _PRINTING_TECHNIQUE_MAP.get(technique)

        for lcode in SUPPORTED_LANGUAGES:
            if transl_key:
                trans: dict = translations.get(transl_key, {})
                result[lcode].extend(trans[lcode] if lcode in trans else [technique])
            else:
                result[lcode].extend([technique])

    return result


def secondary_literature_json_value_translator(values: list, translations: dict) -> dict:
    works: list = []
    for work in values:
        reference: Optional[str] = work.get("reference")
        number_page: Optional[str] = f"{n}" if (n := work.get("number_page")) else None
        ref = ", ".join(f for f in [reference, number_page] if f)
        works.append(ref)

    return {"none": works}


def scoring_json_value_translator(values: list, translations: dict) -> dict:
    # Simply coalesces the instrumentation into a single list from a JSON
    # list taken from Solr. Does not do any translations of the instrumentation
    # (yet).
    instruments: list = []
    for inst in values:
        voice: Optional[str] = inst.get("voice_instrument")
        num: Optional[str] = f'({n})' if (n := inst.get("number")) else None
        instrument = " ".join([f for f in [voice, num] if f])
        instruments.append(instrument)

    return {"none": instruments}


def dramatic_roles_json_value_translator(values: list, translations: dict) -> dict:
    """
    Doesn't actually do any translation, but will consume a list of JSON values and
    produce a single string from them.
    :param values: A list of values from the dramatic_roles_json field
    :param translations: A translations dictionary. Unused.
    :return: A language map containing all the named dramatic roles.
    """
    roles: list = []
    for r in values:
        standard: str = f"{r.get('standard_spelling', '')}"
        source: Optional[str] = f"[{s}]" if (s := r.get('source_spelling')) else None
        role = " ".join(f for f in [source, standard] if f)
        roles.append(role)
    return {"none": roles}


def title_json_value_translator(values: list, translations: dict) -> dict:
    """
    Provides translations for a JSON field value. Inspects all the values and then
    returns all the different variants of the title.

    This means that it takes a bunch of statements and transforms it to something like:

    {"en": ["Some title (Arrangement)"],
    "de": ["Some title (Bearbeitung)"],
    "pl": ["Some title (Aranżacja)"],
    ...}

    Consult the `utitlities.get_titles` function in the indexer for more information
    on how this data is structured.

    :param values: A JSON field. This *must* be a List, which it should be if it comes from Solr.
    :param translations: A dictionary of available field label translations
    :return: A set of translated titles.
    """
    result: dict = {k: [] for k in SUPPORTED_LANGUAGES}

    # Get the individual fields for each entry in the title field, if any.
    for v in values:
        title = v.get("title", "[Without title]")
        subheading = v.get("subheading")
        arrangement = v.get("arrangement")
        key_mode = v.get("key_mode")
        scoring = ", ".join(v.get("scoring_summary", []))
        catalogue_numbers = ", ".join(v.get("catalogue_numbers", []))
        subheading_trans = arrangement_trans = key_mode_trans = {}

        if subheading:
            subheading_trans = subheading_value_translator(subheading, translations)

        if arrangement:
            arrangement_trans = arrangement_statement_value_translator(arrangement, translations)

        if key_mode:
            key_mode_trans = key_mode_value_translator(key_mode, translations)

        for lang in SUPPORTED_LANGUAGES:
            subh = ", ".join(subheading_trans.get(lang, []))
            arrh = ", ".join(arrangement_trans.get(lang, []))
            keyh = ", ".join(key_mode_trans.get(lang, []))
            full_title_components: list = [title, keyh, subh, arrh, scoring, catalogue_numbers]
            full_title = "; ".join([f.strip() for f in full_title_components if f])
            result[lang].append(full_title)

    return result


def key_mode_value_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _KEY_MODE_MAP)


def subheading_value_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _SUBHEADING_MAP)


def arrangement_statement_value_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _ARRANGEMENT_MAP)


def clef_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _CLEF_MAP)


def id_translator(value: str, translations: dict) -> dict:
    """
    Strips an ID prefix off a Solr index so that we can return the bare ID
    as part of a record display. Uses ID_SUB regex to strip the prefix
    ("source_12345" -> "12345")

    :param value:
    :param translations:
    :return: Language Map value for RISM ID
    """
    idval: str = re.sub(ID_SUB, "", value)
    return {"none": [idval]}
