import collections
import glob
from typing import Dict, Union, Optional, List
import yaml
import os
import logging

log = logging.getLogger(__name__)


def __flatten(d: Dict) -> Dict:
    out: Dict = {}
    for key, val in d.items():
        if isinstance(val, dict):
            val = [val]

        if isinstance(val, list):
            for subdict in val:
                deeper = __flatten(subdict).items()
                out.update({key + '.' + key2: val2 for key2, val2 in deeper})
        else:
            out[key] = val
    return out


def load_translations(path: str) -> Optional[Dict]:
    """Takes a path to a set of locale yml files, and returns a dictionary of translations, with each unique key
        pointing to all available translations of that key. For example:

       {"general.editor_help": {
            "en": ["Editor Help"],
            "de": ["Editor Hilfe"],
            "fr": ["Aide pour l'editor"].
            ...
       }}

       The translations are wrapped in a list so that they can be used directly as part of a JSON-LD language map
       structure.
    """
    if not os.path.exists(path):
        log.error("The path for loading the language files does not exist: %s", path)
        return None

    locale_files: List = glob.glob(f"{path}/*.yml")
    output: Dict = collections.defaultdict(dict)

    for locale_file in locale_files:
        log.debug("Opening %s", locale_file)
        try:
            locale_contents: Dict = yaml.safe_load(
                open(locale_file, "r")
            )
        except yaml.YAMLError:
            log.error("Problem loading locale %s; It was skipped.", locale_file)
            continue

        lang, ext = os.path.splitext(os.path.basename(locale_file))

        try:
            translations: Dict = locale_contents[lang]
        except KeyError:
            log.error("The locale in the filename does not match the contents of the file: %s", locale_file)
            continue

        flattened_translations: Dict = __flatten(translations)

        for translation_key, translation_value in flattened_translations.items():
            if translation_value:
                output[translation_key].update({lang: [translation_value]})

    return dict(output) or None
