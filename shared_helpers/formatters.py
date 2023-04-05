from typing import Optional

from shared_helpers.display_translators import title_json_value_translator


def format_work_label(obj: dict) -> str:
    title: str = obj.get("standard_title_s")
    catalogue: str = f" {obj.get('catalogue_s', '')}."
    catalogue_num: str = f" {obj.get('number_page_s')}"

    return f"{title} {catalogue}{catalogue_num}"


def format_source_label(std_title: list, translations: dict) -> dict:
    return title_json_value_translator(std_title, translations)


def format_institution_label(obj: dict) -> str:
    city = siglum = department = ""

    # prefer institution records with 'name_s', but if used in
    # holdings, then the field is 'institution_name_s'. Fall back
    # to "[No name]" if neither is found.
    name: Optional[str] = obj.get("name_s")
    if not name:
        name = obj.get("institution_name_s", "[No name]")

    if 'department_s' in obj:
        department = f", {obj['department_s']}"
    if 'city_s' in obj:
        city = f", {obj['city_s']}"
    if 'siglum_s' in obj:
        siglum = f" ({obj['siglum_s']})"

    return f"{name}{department}{city}{siglum}"


def format_person_label(obj: dict) -> str:
    name: str = obj.get("name_s")
    dates: str = f" ({d})" if (d := obj.get("date_statement_s")) else ""

    return f"{name}{dates}"


def format_incipit_label(obj: dict) -> str:
    """
    :param obj: A Solr result object containing an incipit record
    :return: A string of the composite title
    """
    work_num: str = obj['work_num_s']
    title: str = f" {' '.join(d)}" if (d := obj.get("titles_sm", [])) else ""

    return f"{work_num}{title}"


def format_source_description(obj: dict) -> str:
    composers: str = ""
    people: str = ""
    source_title: str = ""

    if "source_member_composers_sm" in obj:
        composers = "; ".join(obj["source_member_composers_sm"])

    if "people_names_sm" in obj:
        people = "; ".join(obj["people_names_sm"])

    if "source_title_s" in obj:
        source_title = obj["source_title_s"]

    return f"{source_title} {composers} {people}"


def format_person_description(obj: dict) -> str:
    places: str = ""
    profession: str = ""

    if "place_names_sm" in obj:
        places = "; ".join(obj["place_names_sm"])

    if "profession_function_sm" in obj:
        profession = "; ".join(obj["profession_function_sm"])

    return f"{places} {profession}"


def format_institution_description(obj: dict) -> str:
    address: str = ""

    if "street_address_sm" in obj:
        address = " ".join(obj["street_address_sm"])

    return f"{address}"
