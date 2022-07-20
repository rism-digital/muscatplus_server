from typing import Optional


def format_source_label(obj: dict) -> str:
    title: str = obj.get("main_title_s", "[No title]")
    #  TODO: Translate source types
    source_types: Optional[list] = obj.get("material_group_types_sm")
    shelfmark: Optional[str] = obj.get("shelfmark_s")
    siglum: Optional[str] = obj.get("siglum_s")

    label: str = title
    if source_types:
        label = f"{label}; {', '.join(source_types)}"
    if siglum and shelfmark:
        label = f"{label}; {siglum} {shelfmark}"

    return label


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
    The format for incipit titles is:

    Source title: Work num (supplied title)

    e.g., "Overtures - winds, stck: 1.1.1 (Allegro)"

    If the supplied title is not on the record, it will be omitted.

    :param obj: A Solr result object containing an incipit record
    :return: A string of the composite title
    """
    work_num: str = obj['work_num_s']
    # source_title: str = obj["main_title_s"]
    title: str = f" ({d})" if (d := obj.get("title_s")) else ""

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
