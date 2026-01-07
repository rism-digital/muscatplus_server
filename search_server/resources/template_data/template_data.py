import textwrap
from urllib.parse import urljoin

import orjson
import ypres

from search_server.helpers.display_translators import SOURCE_SIGLA_COUNTRY_MAP
from search_server.helpers.formatters import (
    format_institution_description,
    format_institution_label,
    format_person_description,
    format_person_label,
    format_source_description,
    format_work_description,
    format_work_label,
)
from search_server.resources.countries.country import CountryList


def extract_page_label(obj: dict) -> str:
    if "label" not in obj:
        return "RISM Online"
    elif "en" in obj["label"]:
        return obj["label"]["en"][0]
    elif "none" in obj["label"]:
        return obj["label"]["none"][0]
    return "RISM Online"


class TemplateData(ypres.DictSerializer):
    record_url = ypres.MethodField()
    record_data = ypres.MethodField()
    record_created = ypres.MethodField()
    record_updated = ypres.MethodField()
    country_list_data = ypres.MethodField()

    def get_record_data(self, obj: dict) -> str:
        return orjson.dumps(obj).decode("utf-8")

    def get_country_list_data(self, obj: dict) -> str:
        req = self.context["request"]
        country_list: dict = CountryList(
            SOURCE_SIGLA_COUNTRY_MAP, context={"request": req, "direct_request": True}
        ).serialized
        return orjson.dumps(country_list).decode("utf-8")

    def get_record_url(self, obj: dict) -> str | None:
        return obj["id"]

    def get_record_image_url(self, obj: dict) -> str | None:
        """
        Creates a URL to an image in the form of:

        https://rism.online/og/img/10/source_123410.png

        :param obj:
        :return:
        """
        if obj["type"] not in ("rism:Source",):
            return None

        return urljoin(obj["id"], "image.png")

    def get_record_created(self, obj: dict) -> str | None:
        return None

    def get_record_updated(self, obj: dict) -> str | None:
        return None


class SourceTemplateData(TemplateData):
    record_title = ypres.MethodField()
    record_description = ypres.MethodField()
    record_image_url = ypres.MethodField()

    def get_record_title(self, obj: dict) -> str:
        return extract_page_label(obj)

    def get_record_description(self, obj: dict) -> str | None:
        return None

    def get_record_image_url(self, obj: dict) -> str | None:
        return f"{obj['id']}/image.png"


class PersonTemplateData(TemplateData):
    record_title = ypres.MethodField()
    record_description = ypres.MethodField()
    record_image_url = ypres.MethodField()

    def get_record_title(self, obj: dict) -> str:
        return extract_page_label(obj)

    def get_record_description(self, obj: dict) -> str | None:
        return None

    def get_record_image_url(self, obj: dict) -> str | None:
        return f"{obj['id']}/image.png"


class InstitutionTemplateData(TemplateData):
    record_title = ypres.MethodField()
    record_description = ypres.MethodField()
    record_image_url = ypres.MethodField()

    def get_record_title(self, obj: dict) -> str:
        return extract_page_label(obj)

    def get_record_description(self, obj: dict) -> str | None:
        return None

    def get_record_image_url(self, obj: dict) -> str | None:
        return f"{obj['id']}/image.png"


class WorkTemplateData(TemplateData):
    record_title = ypres.MethodField()
    record_description = ypres.MethodField()
    record_image_url = ypres.MethodField()

    def get_record_title(self, obj: dict) -> str:
        return extract_page_label(obj)

    def get_record_description(self, obj: dict) -> str | None:
        return None

    def get_record_image_url(self, obj: dict) -> str | None:
        return f"{obj['id']}/image.png"


class PublicationTemplateData(TemplateData):
    record_title = ypres.MethodField()
    record_description = ypres.MethodField()
    record_image_url = ypres.MethodField()

    def get_record_title(self, obj: dict) -> str:
        return extract_page_label(obj)

    def get_record_description(self, obj: dict) -> str | None:
        return None

    def get_record_image_url(self, obj: dict) -> str | None:
        return f"{obj['id']}/image.png"


class FrontTemplateData(TemplateData):
    record_title = ypres.MethodField()
    record_description = ypres.MethodField()
    record_image_url = ypres.MethodField()

    def get_record_title(self, obj: dict) -> str:
        return extract_page_label(obj)

    def get_record_description(self, obj: dict) -> str | None:
        return None

    def get_record_image_url(self, obj: dict) -> str | None:
        return None


class AboutTemplateData(TemplateData):
    record_title = ypres.MethodField()
    record_description = ypres.MethodField()
    record_image_url = ypres.MethodField()

    def get_record_title(self, obj: dict) -> str:
        return "RISM Online: About"

    def get_record_description(self, obj: dict) -> str | None:
        return None

    def get_record_image_url(self, obj: dict) -> str | None:
        return None


class CardIcons:
    PERSON = "person"
    PEOPLE = "people"
    INSTITUTION = "institution"
    PLACE = "place"
    ROLE = "role"
    DATE = "date"
    CONTENT = "content"
    SOURCE = "source"


class OpenGraphSvg(ypres.DictSerializer):
    record_type = ypres.StrField("type")
    record_title = ypres.MethodField()
    record_first_line = ypres.MethodField()
    record_second_line = ypres.MethodField()
    record_third_line = ypres.MethodField()

    def get_record_title(self, obj: dict) -> list[str]:
        # Returns a list that can be iterated on in the template. Must be
        # no longer than two elements. The textwrap library imposes these
        # constraints automatically.
        title: str

        if obj["type"] == "source":
            main_title: str = obj.get("main_title_s", "[No title]")
            #  TODO: Translate source types
            source_types: list | None = obj.get("material_source_types_sm")
            shelfmark: str | None = obj.get("shelfmark_s")
            siglum: str | None = obj.get("siglum_s")

            label: str = main_title
            if source_types:
                label = f"{label}; {', '.join(source_types)}"
            if siglum and shelfmark:
                label = f"{label}; {siglum} {shelfmark}"

            title = label
        elif obj["type"] == "person":
            title = format_person_label(obj)
        elif obj["type"] == "institution":
            title = format_institution_label(obj)
        else:
            return ["[Unknown title]"]

        tw: list = textwrap.wrap(title, width=36, max_lines=2)

        return tw

    # These lines return a tuple of (icon, text). If the return value is
    # None then this line will be omitted. The icon names are defined in the
    # CardIcons class above, and correspond to a CSS rule in the SVG template.
    def get_record_first_line(self, obj: dict) -> tuple[str, str] | None:
        objtype: str = obj["type"]

        if (t := obj.get("creator_name_s")) and objtype == "source":
            return CardIcons.PERSON, t
        elif (t := obj.get("source_member_composers_sm")) and objtype == "source":
            member_list = textwrap.shorten("; ".join(t), width=40)
            return CardIcons.PEOPLE, member_list
        elif (
            (t := obj.get("total_sources_i"))
            and objtype == "person"
            or (t := obj.get("total_sources_i"))
            and objtype == "institution"
        ):
            src: str = "sources" if t > 1 else "source"
            label: str = f"Related to {t:,} {src}"
            return CardIcons.SOURCE, label
        return None

    def get_record_second_line(self, obj: dict) -> tuple[str, str] | None:
        objtype: str = obj["type"]

        if (t := obj.get("date_statements_sm")) and objtype == "source":
            label: str = "; ".join(t)
            return CardIcons.DATE, label
        return None

    def get_record_third_line(self, obj: dict) -> tuple[str, str] | None:
        objtype: str = obj["type"]

        label: str
        if (t := obj.get("num_source_members_i")) and objtype == "source":
            label = f"{t} item{'s'[: t ^ 1]} in this source"
            return CardIcons.CONTENT, label
        elif (t := obj.get("num_holdings_i")) and objtype == "source":
            cpy: str = "copy" if t == 1 else "copies"
            label = f"{t} {cpy} of this print"
            return CardIcons.CONTENT, label
        return None
