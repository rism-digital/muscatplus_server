The Search API, accessed primarily through the `/search` path, provides a set of query parameters for performing
searches against the RISM data, and retrieving results in a machine-readable format. These filters are dependent on the
search "mode" that you are in. For example, different filters will apply when you are searching for sources than when
you are searching for people.

Search API responses will contain enough information to construct search queries. But before explaining how this works,
a brief overview of the types of parameters may help.

### Mode

The `mode` parameter is a non-repeatable query argument, and it sets the type of documents you wish to search. The
only allowed values are `sources`, `people`, `instiutions`, and `incipits`. The options available to you will vary
by the selected mode -- for example, you cannot perform an incipit search, using incipit search parameters, when in
`institutions` mode.

If no mode is explicitly set, the default is `sources`.

### Query

The Query parameter, `q`, is a non-repeatable query argument; only one `q` value may be provided in any string of
query parameters. This will perform a full-text keyword search on the documents that are limited by the mode; so,
a `q` parameter will perform a keyword search on all source documents when the sources mode is selected.

### Filters

The list of available filters per mode can be found in the [modes](modes.md) documentation. For each filter there
will be an alias given, and a type. The query argument is `fq`.

The structure of a filter query argument is: `fq=alias:value`, where `alias` is the alias provided in the documentation,
and `value` is dependent on the type of the filter.

There are four primary types of filters:

- `select`: Renders all the available values for a given field as a list of options; in the UI this is presented as
  a set of checkboxes to be selected.
- `toggle`: A true/false toggle switch. The behaviour of this filter varies on what the default `active value` is.
  An active value of `false` means that, when activated, all documents that meet this condition are
  **excluded** from the list of results. Likewise, an active value of `true` means that, when activated,
  the list of results will **only** include results that meet this condition.
- `range`:  The filter accepts a numeric range of values. This is in the format of `[lower TO upper]`. An asterisk, `*`
  means that range is unbounded. `[1820 TO 1840]` retrieves all documents for which the filter field has
  values between those ranges. `[* TO 1840]` retrieves all documents up to and including 1840.
- `query`:  The filter accepts partial values as a full-text lookup. For example, you could use a value of `Mozart*` to
  find all values for that field that start with "Mozart". Fields that are marked as query fields can also
  be used with the [`/suggest`](routes.md#suggest) endpoint, passing the alias for this field and retrieving
  a possible list of values.

### Sorting

The `sort` query parameter controls how the search results are sorted. Depending on the search mode selected, different
options are available. See the [modes](modes.md) documentation to see what options are available per node. To choose
a sort option use the `alias` value, e.g., `?sort=alphabetical-name`.

The default sort field is also given in the block. This is the sorting parameter that is used if no sort query
parameter is provided.

### Number of Results

The `rows` query parameter controls how many results are returned per page in the response. There are only three
allowable values, 20 (default), 40, and 100. Any other numbers passed will raise an error.

### National Collections

National collections can be selected with the `nc` query parameter, and the value is the country code that forms
part of the RISM siglum for that country. For example, `?nc=CH` would apply a National Collection filter for
Switzerland, or `?nc=GB` for the United Kingdom.

When a National Collection is selected, the `person` mode is not available. All results in other modes are limited to
those that are directly related to an institution in that country. For source records, this means that there must
be at least one exemplar held in a related institution. Likewise, the National Collection filter for incipits limits the 
search to only sources that are held in a related institution.

## Incipit Search

The incipit notation search has a number of additional query parameters that control the behaviour of the notation 
search. These query parameters may also be combined with some general search query parameters; for example, it is 
possible to search using a `q` (keyword query) and an `n` (notation query) at the same time.

### Notation

The `n` query parameter uses the Plaine & Easie code to send a notation query to the server. This allows for fairly 
complex notation queries. The full range of Plaine & Easie code is supported; however, some components of the notation, 
such as note durations, are currently ignored during search. Measures are also accepted, but ignored. 
(This will likely change in later versions of the incipit search)

In cases where chords are passed, the notation search will only consider the top-most note in the chord for the 
purposes of matching. 

### Incipit search mode

The `im` query parameter can be one of two values, `intervals` and `exact-pitches`. This selects how the notation query 
should be parsed. With `intervals`, the notation string is interpreted as a series of chromatic intervals, allowing the 
same "tune" to be matched regardless of transposition. `exact-pitches`, however, interprets the notation sequence as a 
set of exact note names.

### Incipit clef display

The `ic` query parameter sets the incipit clef, but only for the purposes of visualizing the notation. Including this 
parameter will not affect the results of the search. If you wish to restrict your results to only those with a specific
clef or clefs, it is better to use the clef filter field. It accepts any valid Plaine & Easie clef value. 

### Incipit time signature display

The `it` query parameter sets the rendering of the time signature display. Including this parameter will not affect
the results of the search. If you wish to restrict your results to only those with a specific time signature, it is
better to use the time signature filter field. It accepts any valid Plaine & Easie time signature value.

### Incipit key signature

The `ik` query parameter sets the rendering of the key signature display. This one requires special attention. Setting
a key signature for a query will adjust the intervals of the resulting pitch string. If a key signature of one sharp is
set, then any "F" notes in the query are no longer F naturals, but F sharps. Setting a key signature with `ik` will not
restrict results to only those in that key signature. If you wish to do this, you should use the key signature filter.
The `ik` query parameter accepts any valid Plaine & Easie key signature value.

## Searching for sources in authority records 

Some resource records have a search endpoint where you can perform searches for source records that are automatically 
limited to the relationship with that resource.

For example, Institution resources have a search endpoint that let you search all the source records related to that 
institution, if there are any. Likewise, People resources have a search endpoint that let you search all the source 
records related to that person.

All the query parameters for searching in the `sources` mode apply to these search endpoints.

## Parsing Search API Responses

The Search API will respond with JSON-LD containing all the information you might need to construct another request
to the API. To understand this better we can look at the most important sections of the response.

#### `id`

The `id` parameter always gives the current URL of the search, including all query parameters. This is generally the
same as the URL you might see in the address bar when looking at the HTML rendering of the page, so you can
go between the different representations quite easily.

#### `totalItems`

The total number of items returned for a given search. Always an integer.

#### `view`

The `view` section of the Search API response gives the pagination controls. It will always give an URL to the first
page of results and if other pages are available, then it will also provide links to the next, previous, and last pages.
It will also provide the total number of pages, and the number of the current page.

#### `items`

The list of results. Depending on the search mode, the contents and structure of each result will change.

#### `facets`

The `facets` section contains all the data for constructing a faceted search interface and constructing filter queries.
It will give you the alias, label, and type for each facet, and optionally some extra information for different types
of filters. For example, for Query facets, it will provide you with a pre-built URL for the `/suggest` endpoint.

For filters that support changing the behaviour of the facet, it will also provide you with the available options,
the current option, and the default.

#### `modes`

The `modes` section gives you the available search modes. If you perform a keyword search, it will show you the number
of results that you would retrieve for all other modes.

#### `sorts`

The available options, both labels and values, for the sorting parameters for the selected search mode. The default
sort field is also provided.

#### `pageSizes`

A list of valid page size values.
