from functools import lru_cache
from typing import Dict


@lru_cache(maxsize=2048)
def jsonld_translations(value: str, translations: Dict) -> Dict:
    # Takes a value and matches it against a dictionary of available translations.
    # Used for creating JSON-LD language maps. If no match is found
    # the function returns a language map with `none` as the language key.
    # May be used as:
    #
    #  >> import jsonld_translations as lmap
    #  >> relators: Dict = yaml.full_load("relator-codes.yml")
    #  ...
    #  >> return lmap('art', relators)
    #  {"it": ["Scenografo"],
    #   "fr": ["Metteur en scène"],
    #   "de": ["Bühnenbildner"],
    #   "en": ["Artist"],
    #   "es": ["Puestista"],
    #   "pl": ["Artysta"]}
    #
    #  >> return lmap('foo', relators)
    #  {"none": ["foo"]}
    pass