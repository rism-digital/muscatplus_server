from typing import List, Dict

from search_server.helpers.identifiers import EXTERNAL_IDS


def external_authority_list(authority_list: List) -> List[Dict]:
    externals: List = []
    for ext in authority_list:
        source, ident = ext.split(":")
        base = EXTERNAL_IDS.get(source)
        if not base:
            continue

        label: str = base["label"]
        uri: str = base["ident"].format(ident=ident)

        externals.append({
            "url": uri,
            "label": {"none": [label]},
            "type": source  # todo: convert this to a namespaced URI representing the external authorities.
        })

    return externals
