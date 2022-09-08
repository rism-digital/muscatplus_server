[JSON-LD Language Maps](https://www.w3.org/TR/json-ld11/#language-maps) are used extensively in the RISM Online API
to deliver content in all the languages we support. These language maps are the primary source of translated content
in the user interface, but they are also structured so to be easy for machines to parse them for display in external
systems. Using the labels provided in the language maps helps ensure a consistent set of terminology is used across
all RISM platforms, in all languages.

The language maps we provide come in two primary forms. The first is for non-linguistically identified content. This
is not to say that it has no specific language, but that we have no information about the language used. Frequently,
you may come across records for which the cataloguer has decided to describe the source in their own language, but
we do not capture the language they used for a specific field.

In this case, the language map provided might look something like this:

    "value": {"none": ["Some value"]}

The value of `none` indicates that the language content of `Some value` is unspecified.

The second form is one where we have translations for a given term. In this case, the language map might look
something like this:

```json
"typeLabel": {"pt":["Fonte"],
              "pl":["Źródło"],
              "es":["Fuente"],
              "fr":["Source"],
              "it":["Fonte"],
              "en":["Source"],
              "de":["Quelle"]}
```

Here, each of the different translated terms are identified by their two-letter ISO language code. The `none` key never 
appears in the same LanguageMap as those with actual language values. 

> In the RISM Online User Interface, the language of the user's browser is detected, and the appropriate language
> selected. If a user's browser is set to a different language than is supported, the site will default to the
> English version.

The language maps can contain a list of values, which can be generally interpreted as a list of entries or, in the case
of notes fields, separate paragraphs. So, you may find an entry like this:

```json
"value": {"none":["Chopin, F.",
                  "Chopin, Fr.",
                  "Chopin, Frederick",
                  "Chopin, Frederik",
                  "Chopin, Friedrich",
                  "Chopin, Friedrich Franz",
                  "Chopin, Fryderyk",
                  "Chopin, Fryderyk F.",
                  "Chopin, Fryderyk Franciszek",
                  "Chopin, Frédéric",
                  "Chopin, Frédéric F.",
                  "Chopin, Frédéric François",
                  "Chopin, Frédéric-François",
                  "Sopen, F.",
                  "Sopen, Friderik",
                  "Szopen, Fryderyk",
                  "Szopen, Fryderyk Franciszek"]}
```

When displaying this, it would be appropriate to display all the values in the list.
