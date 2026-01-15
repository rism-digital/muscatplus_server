from sanic.log import logger
import ypres

from search_server.helpers.display_translators import work_catalogue_status_translator
from search_server.helpers.formatters import format_source_label
from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.record_types import create_source_types_block


# TODO: Ensure the required fields are present in the object before serializing
class PartOfSection(ypres.DictSerializer):
    slabel = ypres.MethodField(label="label")
    stype = ypres.StaticField(label="type", value="rism:PartOfSection")
    items = ypres.MethodField()

    def get_slabel(self, obj: dict) -> dict:
        req = self.context["request"]
        transl: dict = req.ctx.translations
        return transl["records.item_part_of"]

    def get_items(self, obj: dict) -> list | None:
        req = self.context["request"]
        transl: dict = req.ctx.translations

        obj_type = obj["type"]
        match obj_type:
            case "work":
                all_catalogues = [_get_work_part_of(req, obj, transl)]
                alt_publications: list | None = obj.get(
                    "secondary_works_catalogue_json"
                )
                if not alt_publications:
                    return all_catalogues

                for wp in alt_publications:
                    all_catalogues.append(_get_work_block(req, wp, transl))

                return all_catalogues
            case "source":
                # A special case where the list of incipits for a source is rendered from the Source record.
                # The context will have "primary": "incipit" on it to differentiate.
                if self.context.get("primary") == "incipit":
                    return [_get_source_part_of(req, obj, transl)]
                return [_get_source_member_part_of(req, obj, transl)]

            case "incipit":
                return [_get_incipit_part_of(req, obj, transl)]
            case "holding":
                return [_get_source_part_of(req, obj, transl)]
            case "dobject":
                return [_get_dobject_part_of(req, obj, transl)]
            case _:
                logger.error(
                    "Could not determine object type %s for %s", obj_type, obj["id"]
                )

        return None


def _get_work_part_of(req, obj: dict, translations: dict) -> dict:
    wc = obj.get("works_catalogue_json")
    return _get_work_block(req, wc[0], translations, is_primary=True) if wc else {}


def _get_work_block(
    req, wc: dict, translations: dict, is_primary: bool = False
) -> dict:
    wc_id = strip_prefix(wc["id"])
    type_label: dict = translations["records.work_catalog"]

    short_name: str | None = wc.get("short_name")
    page_number: str | None = wc.get("pages")

    work_number: str
    if short_name and page_number:
        work_number = f"{short_name} {page_number}"
    else:
        work_number = "[No identifier]"

    return {
        "relationshipType": "rism:PrimaryPartOf"
        if is_primary
        else "rism:SecondaryPartOf",
        "relatedTo": {
            "id": get_identifier(req, "publications.publication", publication_id=wc_id),
            "label": {"none": [wc["title"]]},
            "type": "rism:Publication",
            "typeLabel": type_label,
            "status": {
                "label": work_catalogue_status_translator(
                    wc["work_catalogue_status"], translations
                ),
                "value": wc["work_catalogue_status"],
            },
        },
        "workNumber": work_number,
    }


def _get_source_part_of(req, obj: dict, translations: dict) -> dict:
    obj_type = obj["type"]
    if obj_type == "holding":
        obj_id = strip_prefix(obj["source_id"])
    else:
        obj_id = strip_prefix(obj["id"])
    ident: str = get_identifier(req, "sources.source", source_id=obj_id)

    # if "standard_titles_json" not in obj:
    #     label = {"none": [obj.get("main_title_s", "[No title]")]}
    # else:
    label = format_source_label(obj["standard_titles_json"], translations)

    source_type: str = obj.get("source_type_s", "unspecified")
    content_identifiers: list[str] = obj.get("content_types_sm", [])
    record_type: str = obj.get("record_type_s", "item")

    source_types_block = create_source_types_block(
        record_type, source_type, content_identifiers, translations
    )

    return {
        "relationshipType": "rism:PrimaryPartOf",
        "relatedTo": {
            "id": ident,
            "type": "rism:Source",
            "typeLabel": translations.get("records.source"),
            "sourceTypes": source_types_block,
            "label": label,
        },
    }


def _get_source_member_part_of(req, obj: dict, translations: dict) -> dict:
    source_membership: dict = obj.get("source_membership_json", {})
    parent_source_id: str = strip_prefix(source_membership.get("source_id", ""))

    ident: str = get_identifier(req, "sources.source", source_id=parent_source_id)
    parent_title: str = source_membership.get("main_title", "[No title]")
    parent_shelfmark: str | None = source_membership.get("shelfmark")
    parent_siglum: str | None = source_membership.get("siglum")
    parent_material_types: list | None = source_membership.get("material_types")

    # NB: This should match the format in formatters.format_source_label! But since
    # we're dealing with a JSON field the names are different, and we only do this
    # once in the whole app.
    label: str = parent_title
    if parent_material_types:
        label = f"{label}; {', '.join(parent_material_types)}"
    if parent_siglum and parent_shelfmark:
        label = f"{label}; {parent_siglum} {parent_shelfmark}"

    record_type: str = source_membership.get("record_type", "item")
    source_type: str = source_membership.get("source_type", "unspecified")
    content_types: list[str] = source_membership.get("content_types", [])

    source_types_block: dict = create_source_types_block(
        record_type, source_type, content_types, translations
    )

    return {
        "relationshipType": "rism:PrimaryPartOf",
        "relatedTo": {
            "id": ident,
            "type": "rism:Source",
            "typeLabel": translations.get("records.source"),
            "sourceTypes": source_types_block,
            "label": {"none": [label]},
        },
    }


def _get_incipit_part_of(req, obj: dict, translations: dict) -> dict:
    parent_object_type: str = obj["parent_type_s"]

    match parent_object_type:
        case "source":
            label = format_source_label(obj["standard_titles_json"], translations)
            source_id: str = strip_prefix(obj["source_id"])
            record_type: str = obj.get("record_type", "item")
            source_type: str = obj.get("source_type", "unspecified")
            content_types: list[str] = obj.get("content_types", [])

            source_types_block: dict = create_source_types_block(
                record_type, source_type, content_types, translations
            )
            return {
                "relationshipType": "rism:PrimaryPartOf",
                "relatedTo": {
                    "id": get_identifier(req, "sources.source", source_id=source_id),
                    "type": "rism:Source",
                    "typeLabel": translations.get("records.source"),
                    "sourceTypes": source_types_block,
                    "label": label,
                },
            }
        case "work":
            work_id: str = strip_prefix(obj["id"])
            return {
                "relationshipType": "rism:PrimaryPartOf",
                "relatedTo": {
                    "id": get_identifier(req, "works.work", work_id=work_id),
                    "type": "rism:Work",
                    "typeLabel": translations["records.work"],
                    "label": {"none": [obj.get("standard_title_s")]},
                },
            }
        case _:
            return {}


def _get_dobject_part_of(req, obj: dict, translations: dict) -> dict:
    linked_record_type: str = obj["linked_type_s"]
    linked_id_val: str = obj["linked_id"]
    linked_id: str = strip_prefix(linked_id_val)
    label = {"none": [f"{obj.get('linked_name_s', '[No name]')}"]}

    related_to: dict
    if linked_record_type == "source":
        related_to = {
            "id": get_identifier(req, "sources.source", source_id=linked_id),
            "label": label,
            "type": "rism:Source",
        }
    elif linked_record_type == "person":
        related_to = {
            "id": get_identifier(req, "people.person", person_id=linked_id),
            "label": label,
            "type": "rism:Person",
        }
    elif linked_record_type == "holding":
        # Get the source ID from the request path.
        source_id: str = req.match_info.get("source_id", "no-id")
        related_to = {
            "id": get_identifier(
                req, "sources.holding", source_id=source_id, holding_id=linked_id
            ),
            "label": label,
            "type": "rism:Exemplar",
        }
    elif linked_record_type == "institution":
        related_to = {
            "id": get_identifier(
                req, "institutions.institution", institution_id=linked_id
            ),
            "label": label,
            "type": "rism:Institution",
        }
    else:
        logger.error("Could not determine part-of for %s", obj["id"])
        related_to = {
            "id": "no-id",
            "type": "rism:UnknownObject",
            "label": label,
        }

    return {
        "relationshipType": "rism:PrimaryPartOf",
        "relatedTo": related_to,
    }
