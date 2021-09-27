from typing import Optional

from small_asc.client import Results

from search_server.helpers.search_request import sorting_for_mode


def get_sorting(req, obj: Results) -> Optional[list]:
    cfg: dict = req.app.ctx.config
    transl: dict = req.app.ctx.translations
    current_mode: str = req.args.get("mode", cfg["search"]["default_mode"])
    sorts: list = sorting_for_mode(cfg, current_mode)

    sorting_options: list = []

    for sortcfg in sorts:
        translation_key: str = sortcfg['label']
        translation: Optional[dict] = transl.get(translation_key)

        label: dict
        if translation:
            label = translation
        else:
            label = {"none": [translation_key]}

        sorting_options.append({
            "label": label,
            "alias": sortcfg.get("alias")
        })

    return sorting_options
