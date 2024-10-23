from typing import Optional

from search_server.helpers.search_request import sorting_for_mode


def get_sorting(req, is_contents: bool = False) -> Optional[dict]:
    """
    If the sorting config is being loaded for a source contents page, then set the
    is_contents flag to `True`. This will add any sort parameters that are marked
    as `only_contents` in the config.

    :param req: A request object
    :param is_contents: True if we're on a Source contents page; false otherwise
    :return: A list of available sorting options.
    """
    cfg: dict = req.app.ctx.config
    transl: dict = req.app.ctx.translations
    current_mode: str = req.args.get("mode", cfg["search"]["default_mode"])
    sorts: list = sorting_for_mode(cfg, current_mode)

    sorting_options: list = []
    sort_block: dict = {}
    sort_default: str = ""

    for sortcfg in sorts:
        only_contents: bool = sortcfg.get("only_contents", False)
        # This somewhat cryptic check looks to see if we're processing a block marked
        # as being only applicable for the contents search, and checks if the serializer
        # is being called on a search that is the contents page. If we have an only_contents
        # block, but we're not on a contents page, skip processing this block.
        if only_contents and not is_contents:
            continue

        is_defaultcfg = sortcfg.get("default", False)
        cfg_alias: str = sortcfg["alias"]

        # Choose the *first* block marked as a default.
        if not sort_default and is_defaultcfg is True:
            sort_default = cfg_alias

        translation_key: str = sortcfg["label"]
        translation: Optional[dict] = transl.get(translation_key)
        label: dict = translation or {"none": [translation_key]}

        sorting_options.append({"label": label, "alias": cfg_alias})

    sort_block["options"] = sorting_options
    sort_block["default"] = sort_default

    return sort_block
