import textwrap
import yaml

from search_server.server import app

INCLUDE_ROUTES: list = [
    "people/<person_id:str>",
    "people/<person_id:str>/sources",
    "institutions/<institution_id:str>",
    "institutions/<institution_id:str>/sources",
    "sources/<source_id:str>",
    "sources/<source_id:str>/contents",
    "/<source_id:str>/incipits/<work_num:str>/",
    "search",
    "probe",
    "suggest"
]


route_template: str = """
### `/{route_name}`
{docstring}
"""

filter_section_tmpl: str = """
## {mode} Mode

### Filters

The available filters for the {mode} mode are:

{filterbody}

### Sorting

The available options for sorting results for the {mode} mode are:

{sortbody}
"""

select_filter_description_tmpl: str = """
#### {label}

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq={alias}:"Some value"&fq={alias}:"Some other value"&fb={alias}:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `{alias}`

Type
: `{type}`

Values
: Any string value 

Default behaviour
: `{default_behaviour}`

Default sort
: `{default_sort}`
"""

toggle_filter_description_tmpl: str = """
#### {label}

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `{alias}`

Type
: `{type}`

Values
: Boolean, `true` or `false`.

Active value
: `{active_value}`.  

Example
: `?fq={alias}:false`
"""

range_filter_description_tmpl: str = """
#### {label}

Alias
: `{alias}`

Type
: `{type}`

Values
: A range of numbers, formatted in square brackets separated by `TO`, e.g., `[1875 TO 1880]`. A `*` indicates an
unbounded upper or lower limit, e.g., `[* TO 1880]` would find all numbers up to 1880.

Example
: `?fq={alias}:[1875 TO 1880]`
"""

query_filter_description_tmpl: str = """
#### {label}

Alias
: `{alias}`

Type
: `{type}`

Values
: A fixed value, or a value using a wildcard to retrieve all matching values. For example, a value of `Mozart*` will
filter the results for any results in this field that start with `Mozart` but vary in their ending. 

Example
: `?fq={alias}:Mozart*`
"""

sorting_tmpl: str = """
#### {label}

Alias
: `{alias}`

"""


def main():
    all_routes: dict = app.router.routes_all
    sorted_routes = sorted(all_routes.items(), key=lambda tup: tup[1].path)
    with open("docs/api/routes.md", "w") as opn:
        for rt, fn in sorted_routes:
            print(f"Route: {fn.path}")
            if fn.path not in INCLUDE_ROUTES:
                print(f"Skipping {fn.path}.")
                continue

            docstring: str = textwrap.dedent(fn.handler.__doc__) if fn.handler.__doc__ else ""

            route_name = fn.path
            tpl = route_template.format(route_name=route_name, docstring=docstring)
            opn.writelines(tpl)

    with open("docs/api/modes.md", "w") as opn:
        config: dict = yaml.safe_load(open('configuration.yml', 'r'))
        for section, sectcfg in config["search"]["modes"].items():
            sname = section.capitalize()

            filterbody = ""

            for filt in sectcfg["filters"]:
                filtlabel = filt["label"]
                filtalias = filt["alias"]
                if filtlabel in app.ctx.translations:
                    label = app.ctx.translations[filtlabel]["en"][0]
                else:
                    label = filtlabel

                filttype = filt["type"]

                if filttype == "select":
                    default_behaviour = filt.get("default_behaviour") if "default_behaviour" in filt else "intersection"
                    default_sort = filt.get("default_sort") if "default_sort" in filt else "count"
                    filttpl = select_filter_description_tmpl.format(label=label, alias=filtalias, type=filttype,
                                                                    default_behaviour=default_behaviour,
                                                                    default_sort=default_sort)
                elif filttype == "toggle":
                    active_value = str(filt.get("active_value")).lower()
                    filttpl = toggle_filter_description_tmpl.format(label=label, alias=filtalias, type=filttype,
                                                                    active_value=active_value)
                elif filttype == "range":
                    filttpl = range_filter_description_tmpl.format(label=label, alias=filtalias, type=filttype)
                elif filttype == "query":
                    filttpl = query_filter_description_tmpl.format(label=label, alias=filtalias, type=filttype)
                else:
                    filttpl = ""
                filterbody += f"{filttpl}\n"

            sortbody = ""

            for srt in sectcfg["sorting"]:
                sorttpl = sorting_tmpl.format(label=srt["label"], alias=srt["alias"])
                sortbody += f"{sorttpl}\n"

            tpl = filter_section_tmpl.format(mode=sname, filterbody=filterbody, sortbody=sortbody)
            opn.writelines(tpl)


if __name__ == "__main__":
    main()
