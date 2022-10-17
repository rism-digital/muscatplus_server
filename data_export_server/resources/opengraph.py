import re
import textwrap
from typing import Optional
from urllib.parse import urljoin
import serpy

from shared_helpers.formatters import (
    format_source_label,
    format_person_label,
    format_institution_label,
    format_source_description,
    format_person_description,
    format_institution_description
)
from shared_helpers.identifiers import ID_SUB, get_url_from_type, get_site
from shared_helpers.serializers import ContextDictSerializer


class OpenGraph(ContextDictSerializer):
    record_url = serpy.MethodField()
    record_title = serpy.MethodField()
    record_description = serpy.MethodField()
    record_image_url = serpy.MethodField()

    def get_record_url(self, obj: dict) -> str:
        req = self.context.get("request")
        record_id: str = re.sub(ID_SUB, "", obj["id"])
        url = get_url_from_type(req, obj["type"], record_id)

        return url

    def get_record_title(self, obj: dict) -> str:
        if obj["type"] == "source":
            title: str = obj.get("main_title_s", "[No title]")
            #  TODO: Translate source types
            source_types: Optional[list] = obj.get("material_source_types_sm")
            shelfmark: Optional[str] = obj.get("shelfmark_s")
            siglum: Optional[str] = obj.get("siglum_s")

            label: str = title
            if source_types:
                label = f"{label}; {', '.join(source_types)}"
            if siglum and shelfmark:
                label = f"{label}; {siglum} {shelfmark}"

            return label

        elif obj["type"] == "person":
            return format_person_label(obj)
        elif obj["type"] == "institution":
            return format_institution_label(obj)
        else:
            return "[Unknown title]"

    def get_record_description(self, obj: dict) -> str:
        objtype: str = obj["type"]

        if objtype == "source":
            return format_source_description(obj)
        elif objtype == "person":
            return format_person_description(obj)
        elif objtype == "institution":
            return format_institution_description(obj)
        else:
            return "RISM Online"

    def get_record_image_url(self, obj: dict) -> str:
        """
        Creates a URL to an image in the form of:

        https://rism.online/og/img/10/source_123410.png

        :param obj:
        :return:
        """
        req = self.context.get("request")
        site = get_site(req)

        return urljoin(site, f"og/img/{obj['id']}.png")


class CardIcons:
    PERSON = "person"
    PEOPLE = "people"
    INSTITUTION = "institution"
    PLACE = "place"
    ROLE = "role"
    DATE = "date"
    CONTENT = "content"
    SOURCE = "source"


class OpenGraphSvg(ContextDictSerializer):
    record_type = serpy.MethodField()
    record_title = serpy.MethodField()
    record_first_line = serpy.MethodField()
    record_second_line = serpy.MethodField()
    record_third_line = serpy.MethodField()

    def get_record_type(self, obj: dict) -> str:
        return obj["type"]

    def get_record_title(self, obj: dict) -> list[str]:
        # Returns a list that can be iterated on in the template. Must be
        # no longer than two elements. The textwrap library imposes these
        # constraints automatically.
        title: str

        if obj["type"] == "source":
            main_title: str = obj.get("main_title_s", "[No title]")
            #  TODO: Translate source types
            source_types: Optional[list] = obj.get("material_source_types_sm")
            shelfmark: Optional[str] = obj.get("shelfmark_s")
            siglum: Optional[str] = obj.get("siglum_s")

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
    def get_record_first_line(self, obj: dict) -> Optional[tuple[str, str]]:
        objtype: str = obj["type"]

        if (t := obj.get("creator_name_s")) and objtype == "source":
            return CardIcons.PERSON, t
        elif (t := obj.get("source_member_composers_sm")) and objtype == "source":
            member_list = textwrap.shorten("; ".join(t), width=40)
            return CardIcons.PEOPLE, member_list
        elif (t := obj.get("total_sources_i")) and objtype == "person":
            src: str = "sources" if t > 1 else "source"
            label: str = f"Related to {t:,} {src}"
            return CardIcons.SOURCE, label
        elif (t := obj.get("total_holdings_i")) and objtype == "institution":
            src: str = "sources" if t > 1 else "source"
            label: str = f"Related to {t:,} {src}"
            return CardIcons.SOURCE, label
        return None

    def get_record_second_line(self, obj: dict) -> Optional[tuple[str, str]]:
        objtype: str = obj["type"]

        if (t := obj.get("date_statements_sm")) and objtype == "source":
            label: str = "; ".join(t)
            return CardIcons.DATE, label
        return None

    def get_record_third_line(self, obj: dict) -> Optional[tuple[str, str]]:
        objtype: str = obj["type"]

        if (t := obj.get("num_source_members_i")) and objtype == "source":
            itm: str = "items" if t > 1 else "item"
            label: str = f"{t} {itm} in this source"
            return CardIcons.CONTENT, label
        elif (t := obj.get("num_holdings_i")) and objtype == "source":
            cpy: str = "copies" if t > 1 else "copy"
            label: str = f"{t} {cpy} of this print"
            return CardIcons.CONTENT, label
        return None
