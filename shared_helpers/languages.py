import collections
import errno
import glob
import logging
import os
import re
from pathlib import Path
from typing import Optional, Pattern, Union

import yaml

log = logging.getLogger(__name__)

# Removes ruby crud in the YML files.
REMOVE_ACTIVESUPPORT: Pattern = re.compile(r"!map:ActiveSupport::HashWithIndifferentAccess")
# A list of the languages we support
SUPPORTED_LANGUAGES: list = ["de", "en", "es", "fr", "it", "pl", "pt"]


def language_labels(translations: dict) -> dict:
    """
    Loads in the language configuration file and correlates it with the available translations to produce a
    dictionary with the general shape of:

    {...
    "ger": {"en": ["German"],
            "de": ["Deutsch"],
            "fr": ["Allemand"],
            ...}
    ...}

    This uses the 'SharedLanguageLabels.yml' file from Muscat. There is a bit of processing needed to get
    pyyaml happy with that file, since Rails seems to need to inject some custom entries in the yml file.

    Caches the result after constructing it the first time so that subsequent lookups do not need to
    open the file and construct the dictionary again.

    :return: A dictionary of language labels to translated values.
    """
    fn: str = "SharedLanguageLabels.yml"

    if not os.path.exists(fn):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), fn)

    with open(fn, "r") as input_yaml:
        # stripping the ruby-specific tags out with regex is easier than trying to get pyyaml to ignore it. Trust me.
        yml: str = input_yaml.read()
        cleaned_yml: str = re.sub(REMOVE_ACTIVESUPPORT, "", yml)

        try:
            lang_contents: dict = yaml.safe_load(
                cleaned_yml
            )
        except yaml.YAMLError:
            log.error("Problem loading language labels %s; It was skipped.", fn)
            raise

    res: dict = {}
    for abbrev, label in lang_contents.items():
        transl_key: str = label["label"]
        res[abbrev] = translations[transl_key]

    return res


def __flatten(d: dict) -> dict:
    out: dict = {}
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


def load_translations(path: str) -> Optional[dict]:
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
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)

    output: dict = collections.defaultdict(dict)

    for langcode in SUPPORTED_LANGUAGES:
        locale_file: Path = Path(path, f"{langcode}.yml")

        if not locale_file.exists():
            log.warning("%s could not be found; skipping", locale_file)
            continue

        log.debug("Opening translations: %s", locale_file)

        with locale_file.open("r") as file_contents:
            locale_contents = yaml.safe_load(file_contents)

        if langcode not in locale_contents:
            log.error("The locale in the filename does not match the contents of the file: %s", locale_file)
            continue

        translations: dict = locale_contents[langcode]
        flattened_translations: dict = __flatten(translations)

        for translation_key, translation_value in flattened_translations.items():
            if translation_value:
                output[translation_key].update({langcode: [translation_value]})

    translations: dict = dict(output)

    # combine the translations with the values of the language codes, to keep everything in the same spot.
    # namespace the language codes with 'langcodes' (similar to 'general' or 'records'). Language labels
    # can then be looked up with "langcodes.ger".
    labels: dict = language_labels(translations)
    namespaced_labels: dict = {f"langcodes.{k}": v for k, v in labels.items()}
    translations.update(namespaced_labels)

    return translations


def languages_translator(value: Union[str, list], translations: dict) -> dict:
    """
        A value translator that takes a language code and returns
        the translated value for that language, e.g., "ger" -> "German" for
        English, "Deutsch" for German, etc. Used particularly for the 'LabelConfig' field configurations.
        (see helpers/display_fields.py for more examples of how this is used.)

        Performs a lookup on the translations with a prefixed translation key. See the functions above for
        the special way in which translations for language codes are handled. The above example is
        actually "langcodes.ger", for example.

        Since there could be multiple values, takes a list of language code values and produces a dictionary
        with the values merged. So if the language codes was ["eng", "ger"], the result dictionary would be

        {"en": ["English", "German"],
         "de": ["Englisch", "Deutsch"],
         ...}
    """
    # normalize the incoming value to a list
    if isinstance(value, str):
        trans_value = [value]
    else:
        trans_value = value

    all_values: list[dict] = []
    for v in trans_value:
        trans_key: str = f"langcodes.{v}"
        if trans_key not in translations:
            all_values.append({"none": [v]})
        else:
            all_values.append(translations[trans_key])

    # merge the language values. Uses a set to merge duplicate keys, and a defaultdict so we can gather
    # the keys without checking if they're in lang_dict already and create an empty set.
    lang_dict = collections.defaultdict(set)

    for trans in all_values:
        for k, v in trans.items():
            lang_dict[k].update(v)

    # Unwrap the set into a list for the final result.
    return {k: list(v) for k, v in lang_dict.items()}


def filter_languages(langcodes: set, translations: dict) -> dict:
    return {trans_key:
            {lcode: lvalues for lcode, lvalues in trans_value.items() if lcode in langcodes}
            for trans_key, trans_value in translations.items()}


def negotiate_languages(req, translations: dict) -> dict:
    # If we're not doing any filtering, just return all translations
    if "X-API-Accept-Language" not in req.headers:
        log.debug("No language negotiation")
        return translations

    # If we're requesting all languages anyway
    elif req.headers.get("X-API-Accept-Language") == "*":
        log.debug("All languages negotiated")
        return translations

    lang_values: str = req.headers.get("X-API-Accept-Language")
    split_vals: set = {f.strip() for f in lang_values.split(",")}

    # Take the intersection of requested languages and supported languages. This
    # determines which ones will be in the output.
    acceptable_vals: set = split_vals & set(SUPPORTED_LANGUAGES)

    # If no languages provided are acceptable, return all languages
    if not acceptable_vals:
        log.debug("No acceptable language values requested")
        return translations

    log.debug("filtering languages %s", acceptable_vals)
    return filter_languages(acceptable_vals, translations)
