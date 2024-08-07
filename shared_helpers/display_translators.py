import re
from collections import defaultdict
from typing import Optional, Pattern, Match

from shared_helpers.identifiers import ID_SUB
from shared_helpers.languages import SUPPORTED_LANGUAGES

_MATERIAL_SOURCE_TYPE_MAP: dict = {
    "Manuscript copy": "records.manuscript_copy",
    "Print": "records.print",
    "Autograph manuscript": "records.autograph_manuscript",
    "Possible autograph manuscript": "records.possible_autograph_manuscript",
    "Partial autograph": "records.partial_autograph",
    "Other": "records.other",
    "Manuscript copy with autograph annotations": "records.manuscript_copy_with_autograph_annotations",
    "Print with autograph annotations": "records.print_with_autograph_annotations",
    "Print with non-autograph annotations": "records.print_with_non_autograph_annotations",
    "Composite": "records.composite",
    "Additional printed material": "records.additional_printed_material"
}

_MATERIAL_CONTENT_TYPE_MAP: dict = {
    "Notated music": "records.notated_music",
    "Other": "records.other",
    "Libretto": "records.libretto",
    "Treatise": "records.treatise",
    "Mixed": "records.mixed"
}

_RECORD_TYPE_TRANSLATION_MAP: dict = {
    "single_item": "rism_online.single_item",
    "item": "rism_online.item",
    "collection": "rism_online.collection",
    "composite": "records.composite",
    "work": "records.work"
}

_SOURCE_TYPE_TRANSLATION_MAP: dict = {
    "printed": "rism_online.printed",
    "manuscript": "rism_online.manuscript",
    "composite": "rism_online.composite",
    "unspecified": "records.other"
}

_CONTENT_TYPE_TRANSLATION_MAP: dict = {
    "libretto": "records.libretto",
    "treatise": "records.treatise",
    "musical": "records.notated_music",
    "mixed": "records.mixed",
    "other": "records.other"
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
    None: "records.other",
    "xx": "records.related_institution",
    "now-in": "records.now_in",
    "contained-by": "records.includes_holdings_from",
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
    "bnd": "records.binder",
    "bsl": "records.bookseller",
    "ccp": "records.conceptor",
    "chr": "records.choreographer",
    "cmp": "records.composer",
    "cns": "records.censor",
    "cph": "records.copyright_holder",
    # A special case, where the cre relator code is used to label the 100 main entry field.
    "cre": "records.composer_author",
    "ctb": "records.contributor",
    "dnc": "records.dancer",
    "dnr": "records.donor",
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
    "pat": "records.patron",
    "pbl": "records.publisher",
    "ppm": "records.papermaker",
    "prf": "records.performer",
    "prt": "records.printer",
    "scr": "records.copyist",
    "trl": "records.translator",
    "tyd": "records.type_designer"
}

_PLACE_RELATIONSHIP_LABELS_MAP = {
    None: "records.related_place",
    "xx": "records.related_place",  # special case for un-qualified place relationships
    "go": "records.place_birth",
    "ha": "records.place_origin",
    "so": "records.place_death",
    "wl": "records.country_active",
    "wo": "records.place_active",
    "wr": "records.region_active",
}

_SOURCE_RELATIONSHIP_LABELS_MAP = {
    "rdau:P60191": "relations.P60191",
    "rdau:P60198": "relations.P60198",
    "rdau:P60311": "relations.P60311",
    "rdau:P60312": "relations.P60312",
    "rdau:P60195": "relations.P60195",
    "rdau:P60242": "relations.P60242",
    "rdau:P60274": "relations.P60274",
    "rdau:P60194": "relations.P60194",
    "rdau:P60183": "relations.P60183"
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


_PERSON_GENDER_MAP = {
    None: "general.unknown",
    "male": "general.male",
    "female": "general.female"
}

# These are the countries that currently have sources attached to them. They are separated from
# the full list of countries so that we can expose this publicly as a filter for the UI.
# When a country has sources it should be moved from the full sigla map to this one. If we want to
# remove the ability to filter sources by the country, the country should be removed from this list
# and added to the list below.
SOURCE_SIGLA_COUNTRY_MAP = {
    None: "records.unknown",  # So that we can translate the 'unknown' value as well.
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
    "D": "places.germany",
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
}

# These are the countries that have institutions in them, but no sources -- that is, we have a RISM
# siglum for something in them, but there are no sources catalogued that are held in these countries.
# This list is merged with the source list to create a full listing of all countries.
_FULL_COUNTRY_SIGLA_MAP: dict = {
     "AFG": "places.afghanistan",
     "ARM": "places.armenia",
     "AS": "record.saudi_arabia",
     "AZ": "places.azerbaijan",
     "BD": "places.bangladesh",
     "BG": "places.bulgaria",
     "BIH": "places.bosnia_herzegovina",
     "C": "places.cuba",
     "CR": "places.costa_rica",
     "EC": "places.ecuador",
     "ET": "places.egypt",
     "GE": "places.georgia",
     "IND": "places.india",
     "IR": "places.iran",
     "IRLN": "places.northern_ireland",
     "IS": "places.iceland",
     "KSA": "places.saudi_arabia",
     "L": "places.luxembourg",
     "MC": "places.monaco",
     "MD": "places.moldavia",
     "MNE": "places.montenegro",
     "NIC": "places.nicaragua",
     "NMK": "places.north_macedonia",
     "PK": "places.pakistan",
     "PNG": "places.papua_new_guinea",
     "PRI": "places.puerto_rico",
     "RI": "places.indonesia",
     "RL": "places.lebanon",
     "SRB": "places.serbia",
     "TA": "places.tajikistan",
     "TR": "places.turkey",
     "USB": "places.uzbekistan",
     "XX": "records.unknown",
     "ZA": "places.south_africa"
} | SOURCE_SIGLA_COUNTRY_MAP

_GND_COUNTRY_CODE_MAP: dict = {
    "XA-AD": "places.andorra",
    "XA-AL": "places.albania",
    "XA-AT": "places.austria",
    "XA-AT-2": "places.austria_carinthia",
    "XA-AT-3": "places.austria_lower_austria",
    "XA-AT-4": "places.austria_upper_austria",
    "XA-AT-5": "places.austria_salzburg",
    "XA-AT-6": "places.austria_styria",
    "XA-AT-7": "places.austria_tyrol",
    "XA-AT-9": "places.austria_vienna",
    "XA-BE": "places.belgium",
    "XA-BG": "places.bulgaria",
    "XA-BY": "places.belarus",
    "XA-CH": "places.switzerland",
    "XA-CH-VD": "places.switzerland_vaud",
    "XA-CZ": "places.czech_republic",
    "XA-DE": "places.germany",
    "XA-DE-BY": "places.germany_bavaria",
    "XA-DE-SN": "places.germany_saxony",
    "XA-DK": "places.denmark",
    "XA-EE": "places.estonia",
    "XA-ES": "places.spain",
    "XA-FI": "places.finland",
    "XA-FR": "places.france",
    "XA-GB": "places.uk",
    "XA-GB-NIR": "places.northern_ireland",
    "XA-GR": "places.greece",
    "XA-HR": "places.croatia",
    "XA-HU": "places.hungary",
    "XA-IE": "places.ireland",
    "XA-IS": "places.iceland",
    "XA-IT": "places.italy",
    "XA-IT-32": "places.italy_trentino_alto_adige",
    "XA-LI": "places.liechtenstein",
    "XA-LT": "places.lithuania",
    "XA-LU": "places.luxembourg",
    "XA-LV": "places.latvia",
    "XA-MC": "places.monaco",
    "XA-MD": "places.moldavia",
    "XA-ME": "places.montenegro",
    "XA-MT": "places.malta",
    "XA-NL": "places.netherlands",
    "XA-NO": "places.norway",
    "XA-PL": "places.poland",
    "XA-PT": "places.portugal",
    "XA-RO": "places.romania",
    "XA-RS": "places.serbia",
    "XA-RU": "places.russian_federation",
    "XA-SA": "places.saudi_arabia",
    "XA-SE": "places.sweden",
    "XA-SI": "places.slovenia",
    "XA-SK": "places.slovakia",
    "XA-UA": "places.ukraine",
    "XA-VA": "places.holy_see",
    "XB-AM": "places.armenia",
    "XB-CN": "places.china",
    "XB-GE": "places.georgia",
    "XB-HK": "places.hong_kong",
    "XB-ID": "places.indonesia",
    "XB-IL": "places.israel",
    "XB-IN": "places.india",
    "XB-IQ": "places.iraq",
    "XB-IR": "places.iran",
    "XB-JP": "places.japan",
    "XB-KH": "places.cambodia",
    "XB-KR": "places.korea",
    "XB-PH": "places.philippines",
    "XB-SA": "places.saudi_arabia",
    "XB-SY": "places.syrian_arab_republic",
    "XB-TR": "places.turkey",
    "XB-TW": "places.taiwan",
    "XB-VN": "places.vietnam",
    "XC-BJ": "places.benin",
    "XC-DZ": "places.algeria",
    "XC-EG": "places.egypt",
    "XC-GH": "places.ghana",
    "XC-GN": "places.guinea",
    "XC-UG": "places.uganda",
    "XC-ZA": "places.south_africa",
    "XD-AR": "places.argentina",
    "XD-BO": "places.bolivia",
    "XD-BR": "places.brazil",
    "XD-CA": "places.canada",
    "XD-CL": "places.chile",
    "XD-CO": "places.colombia",
    "XD-CU": "places.cuba",
    "XD-EC": "places.ecuador",
    "XD-GT": "places.guatemala",
    "XD-HN": "places.honduras",
    "XD-JM": "places.jamaica",
    "XD-MX": "places.mexico",
    "XD-NI": "places.nicaragua",
    "XD-PE": "places.peru",
    "XD-PR": "places.puerto_rico",
    "XD-PY": "places.paraguay",
    "XD-SR": "places.suriname",
    "XD-TT": "places.trinidad_tobego",
    "XD-US": "places.usa",
    "XD-UY": "places.uruguay",
    "XD-VE": "places.venezuela",
    "XE-AU": "places.australia",
    "XE-NZ": "places.new_zealand",
    "XE-PG": "places.papua_new_guinea",
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
    :param available_translations: A dictionary of all available translations
    :param translations_map: A dictionary mapping Solr values to the key in the available translations.
    :return: A dictionary corresponding to a language map for that value, selected from the available translations.
    """
    trans_key: Optional[str] = translations_map.get(value)
    if not trans_key:
        return {"none": [value]}
    return available_translations.get(trans_key)


def __lookup_translations_list(values: list, available_translations: dict, translations_map: dict) -> dict:
    """
    Like the function above, but for lists of values instead of a single value.

    :param values:
    :param available_translations:
    :param translations_map:
    :return:
    """
    result: defaultdict = defaultdict(list)

    # NB: we use a fixed key that is likely to always be available in the translations.
    # If this gets changed, this will crash.
    langcodes: list = list(available_translations["general.rism"].keys())

    for trans_itm in values:
        transl_key: Optional[str] = translations_map.get(trans_itm)
        for lcode in langcodes:
            if transl_key:
                trans: dict = available_translations.get(transl_key, {})
                result[lcode].extend(trans[lcode] if lcode in trans else [trans_itm])
            else:
                result[lcode].extend([trans_itm])

    return dict(result)

def record_type_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _RECORD_TYPE_TRANSLATION_MAP)


def source_type_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _SOURCE_TYPE_TRANSLATION_MAP)


def content_type_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _CONTENT_TYPE_TRANSLATION_MAP)


def material_source_types_translator(values: list, translations: dict) -> dict:
    return __lookup_translations_list(values, translations, _MATERIAL_SOURCE_TYPE_MAP)


def material_content_types_translator(values: list, translations: dict) -> dict:
    return __lookup_translations_list(values, translations, _MATERIAL_CONTENT_TYPE_MAP)


def gnd_country_code_labels_translator(values: list, translations: dict) -> dict:
    return __lookup_translations_list(values, translations, _GND_COUNTRY_CODE_MAP)


def country_code_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _FULL_COUNTRY_SIGLA_MAP)


def country_codes_labels_translator(values: list, translations: dict) -> dict:
    return __lookup_translations_list(values, translations, _FULL_COUNTRY_SIGLA_MAP)

def person_name_variant_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _PERSON_NAME_VARIANT_TYPES_MAP)


def person_gender_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _PERSON_GENDER_MAP)


def place_relationship_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _PLACE_RELATIONSHIP_LABELS_MAP)


def source_relationship_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _SOURCE_RELATIONSHIP_LABELS_MAP)


def qualifier_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _QUALIFIER_LABELS_MAP)


def person_institution_relationship_labels_translator(value: str, translations: dict) -> dict:
    return __lookup_translations(value, translations, _PERSON_INSTITUTION_RELATIONSHIP_LABELS_MAP)

def printing_techniques_translator(values: list, translations: dict) -> dict:
    return __lookup_translations_list(values, translations, _PRINTING_TECHNIQUE_MAP)


def secondary_literature_json_value_translator(values: list, translations: dict) -> dict:
    # all_works: { "literature_123": {"formatted": "blah blah", pages: ["12", "13", "14", etc.]} }
    all_works: dict = {}

    for work in values:
        work_id = work.get("id")
        if work_id not in all_works:
            all_works[work_id] = {"formatted": work.get("formatted"), "pages": []}

        if p := work.get("pages"):
            all_works[work_id]["pages"].append(p)

    works: list = []

    for _, fmtwks in all_works.items():
        number_page: str = "; ".join(fmtwks.get("pages", []))
        reference: str = fmtwks.get("formatted", "")
        ref = f"{reference} {number_page}"
        ref += f"{'' if ref.strip().endswith('.') else '.'}"
        works.append(ref)

    return {"none": works}


def scoring_json_value_translator(values: list, translations: dict) -> dict:
    # Simply coalesces the instrumentation into a single list from a JSON
    # list taken from Solr. Does not do any translations of the instrumentation
    # (yet).
    instruments: list = []
    for inst in values:
        voice: str = inst.get("voice_instrument", "")
        num: str = f"({n})" if (n := inst.get("number")) else ""
        instrument = f"{voice} {num}"
        instruments.append(instrument)

    # Format the instrument entry into one string; otherwise the UI will render it
    # as a list of entries.
    instrument_line: str = ", ".join(instruments)

    return {"none": [instrument_line]}


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
    result: defaultdict = defaultdict(list)

    # We use the available translations to know what language codes we should get. To
    # do this we'll take a known value for which it's unlikely it will change, and that will
    # always have all available translations and then get the languages from that.
    langcodes: list = list(translations["general.rism"].keys())

    # Get the individual fields for each entry in the title field, if any.
    for v in values:
        title = v.get("title", "[Without title]")
        subheading: Optional[str] = v.get("subheading")
        arrangement: Optional[str] = v.get("arrangement")
        key_mode: Optional[str] = v.get("key_mode")
        catalogue_numbers: Optional[str] = ", ".join(ch) if (ch := v.get("catalogue_numbers")) else None
        holding_siglum: Optional[str] = v.get("holding_siglum")
        holding_shelfmark: Optional[str] = v.get("holding_shelfmark")
        source_type: str = v.get("source_type", "")
        subheading_trans = arrangement_trans = key_mode_trans = source_type_trans = {}

        if subheading:
            subheading_trans = subheading_value_translator(subheading, translations)

        if arrangement:
            arrangement_trans = arrangement_statement_value_translator(arrangement, translations)

        if key_mode:
            key_mode_trans = key_mode_value_translator(key_mode, translations)

        if source_type:
            source_type_trans = material_source_types_translator([source_type], translations)

        for lang in langcodes:
            tith = f"{title}"
            subh = ', '.join(sh) if (sh := subheading_trans.get(lang, [])) else ""
            arrh = f" {', '.join(ah)}" if (ah := arrangement_trans.get(lang, [])) else ""

            exarr: str = ""
            if subh:
                exarr += subh.strip()
            if arrh:
                exarr += f", {arrh.strip()}" if subh else f"{arrh.strip()}"

            exarr = f" ({exarr})" if exarr else ""
            styp = f"; {', '.join(st)}" if (st := source_type_trans.get(lang, [])) else source_type
            keyh = f"–{', '.join(kh)}" if (kh := key_mode_trans.get(lang, [])) else ""
            cath = f"; {catalogue_numbers}" if catalogue_numbers else ""
            hsigh = f"; {holding_siglum}" if holding_siglum else ""
            hsmh = f" {holding_shelfmark}" if holding_shelfmark else ""

            full_title: str = f"{tith}{keyh}{exarr}{styp}{cath}{hsigh}{hsmh}"

            result[lang].append(full_title)

    return dict(result)


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


URL_DETECTOR: Pattern = re.compile(
    r'(<a href[^>]+>|<a href="")?'
    r'(https?:(?://|\\\\)+'
    r"(?:[\w\d:#@%/;$()~_?+\-=\\.&](?:#!)?)*)",
    flags=re.IGNORECASE)


def _repl_fn(match_obj: Match) -> str:
    href_tag, url = match_obj.groups()
    if href_tag:
        # Since it has an href tag, this isn't what we want to change,
        # so return the whole match.
        return match_obj.group(0)
    else:
        return f"<a href='{url}' target='_blank'>{url}</a>"


def _wrap_addresses(inp: str) -> str:
    return re.sub(URL_DETECTOR, _repl_fn, inp)


def url_detecting_translator(values: list, translations: dict) -> Optional[dict]:
    """
    Detects `http://` and `https://` in a block of text and wraps them in `<a href>` tags
    so that they can be parsed and displayed without a lot of fuss on the front-end.

    The basic methodology of this is taken from https://stackoverflow.com/a/33399083
    """
    wrapped_blocks: list[str] = [_wrap_addresses(s) for s in values]
    if not wrapped_blocks:
        return None

    return {"none": wrapped_blocks}

