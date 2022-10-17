
## Sources Mode

### Filters

The available filters for the Sources mode are:


#### Hide source contents

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `hide-source-contents`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `false`.  

Example
: `?fq=hide-source-contents:false`


#### Hide collection records

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `hide-source-collections`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `false`.  

Example
: `?fq=hide-source-collections:false`


#### Hide composite volumes

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `hide-composite-volumes`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `false`.  

Example
: `?fq=hide-composite-volumes:false`


#### Digital images available

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `has-digitization`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `true`.  

Example
: `?fq=has-digitization:false`


#### IIIF Manifest available

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `has-iiif`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `true`.  

Example
: `?fq=has-iiif:false`


#### Dates

Alias
: `date-range`

Type
: `range`

Values
: A range of numbers, formatted in square brackets separated by `TO`, e.g., `[1875 TO 1880]`. A `*` indicates an
unbounded upper or lower limit, e.g., `[* TO 1880]` would find all numbers up to 1880.

Example
: `?fq=date-range:[1875 TO 1880]`


#### Number of holdings

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=num-holdings:"Some value"&fq=num-holdings:"Some other value"&fb=num-holdings:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `num-holdings`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Type

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=record-type:"Some value"&fq=record-type:"Some other value"&fb=record-type:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `record-type`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Content types

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=content-types:"Some value"&fq=content-types:"Some other value"&fb=content-types:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `content-types`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Material group

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=material-types:"Some value"&fq=material-types:"Some other value"&fb=material-types:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `material-types`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Has incipits

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `has-incipits`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `true`.  

Example
: `?fq=has-incipits:false`


#### Language of text

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=text-language:"Some value"&fq=text-language:"Some other value"&fb=text-language:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `text-language`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Arrangement

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `is-arrangement`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `true`.  

Example
: `?fq=is-arrangement:false`


#### Source holding institution

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=holding-institution:"Some value"&fq=holding-institution:"Some other value"&fb=holding-institution:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `holding-institution`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Subject headings

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=subjects:"Some value"&fq=subjects:"Some other value"&fb=subjects:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `subjects`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Format, extent

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=format-extent:"Some value"&fq=format-extent:"Some other value"&fb=format-extent:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `format-extent`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Composer/Author

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=composer:"Some value"&fq=composer:"Some other value"&fb=composer:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `composer`

Type
: `select`

Values
: Any string value 

Default behaviour
: `union`

Default sort
: `count`


#### Related personal name

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=people:"Some value"&fq=people:"Some other value"&fb=people:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `people`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Is Arrangement

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `is-arrangement`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `true`.  

Example
: `?fq=is-arrangement:false`


#### Scoring summary

Alias
: `scoring`

Type
: `query`

Values
: A fixed value, or a value using a wildcard to retrieve all matching values. For example, a value of `Mozart*` will
filter the results for any results in this field that start with `Mozart` but vary in their ending. 

Example
: `?fq=scoring:Mozart*`


#### Sigla

Alias
: `sigla`

Type
: `query`

Values
: A fixed value, or a value using a wildcard to retrieve all matching values. For example, a value of `Mozart*` will
filter the results for any results in this field that start with `Mozart` but vary in their ending. 

Example
: `?fq=sigla:Mozart*`


#### Related institution

Alias
: `related-institutions`

Type
: `query`

Values
: A fixed value, or a value using a wildcard to retrieve all matching values. For example, a value of `Mozart*` will
filter the results for any results in this field that start with `Mozart` but vary in their ending. 

Example
: `?fq=related-institutions:Mozart*`



### Sorting

The available options for sorting results for the Sources mode are:


#### Most relevant

Alias
: `relevance`



#### Alphabetical (Title, A-Z)

Alias
: `alphabetical-title`



#### Date Added (Newest first)

Alias
: `date-added`




## People Mode

### Filters

The available filters for the People mode are:


#### Dates

Alias
: `date-range`

Type
: `range`

Values
: A range of numbers, formatted in square brackets separated by `TO`, e.g., `[1875 TO 1880]`. A `*` indicates an
unbounded upper or lower limit, e.g., `[* TO 1880]` would find all numbers up to 1880.

Example
: `?fq=date-range:[1875 TO 1880]`


#### Role

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=roles:"Some value"&fq=roles:"Some other value"&fb=roles:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `roles`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Associated place

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=associated-place:"Some value"&fq=associated-place:"Some other value"&fb=associated-place:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `associated-place`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `alpha`


#### Gender

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=gender:"Some value"&fq=gender:"Some other value"&fb=gender:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `gender`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Profession or function

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=profession:"Some value"&fq=profession:"Some other value"&fb=profession:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `profession`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`



### Sorting

The available options for sorting results for the People mode are:


#### Most relevant

Alias
: `relevance`



#### Alphabetical (Name, A-Z)

Alias
: `alphabetical-name`



#### Earliest known date (Oldest first)

Alias
: `earliest-date`



#### Date Added (Newest first)

Alias
: `date-added`



#### Number of sources

Alias
: `num-sources`




## Institutions Mode

### Filters

The available filters for the Institutions mode are:


#### City

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=city:"Some value"&fq=city:"Some other value"&fb=city:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `city`

Type
: `select`

Values
: Any string value 

Default behaviour
: `intersection`

Default sort
: `count`


#### Has siglum

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `has-siglum`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `true`.  

Example
: `?fq=has-siglum:false`



### Sorting

The available options for sorting results for the Institutions mode are:


#### Most relevant

Alias
: `relevance`



#### Alphabetical (Name, A-Z)

Alias
: `alphabetical-name`



#### Date Added (Newest first)

Alias
: `date-added`



#### Number of sources

Alias
: `num-holdings`




## Incipits Mode

### Filters

The available filters for the Incipits mode are:



#### Composer/Author

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=composer:"Some value"&fq=composer:"Some other value"&fb=composer:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `composer`

Type
: `select`

Values
: Any string value 

Default behaviour
: `union`

Default sort
: `count`


#### Dates

Alias
: `date-range`

Type
: `range`

Values
: A range of numbers, formatted in square brackets separated by `TO`, e.g., `[1875 TO 1880]`. A `*` indicates an
unbounded upper or lower limit, e.g., `[* TO 1880]` would find all numbers up to 1880.

Example
: `?fq=date-range:[1875 TO 1880]`


#### Clef

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=clef:"Some value"&fq=clef:"Some other value"&fb=clef:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `clef`

Type
: `select`

Values
: Any string value 

Default behaviour
: `union`

Default sort
: `count`


#### Mensural encoding

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `is-mensural`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `true`.  

Example
: `?fq=is-mensural:false`


#### Has notation

The active value indicates the value that should be passed to activate the toggle. Toggles may be
used to filter results out of a list (an active value of `false`) or indicate that only results matching a filter 
should be kept (an active value of `true`).

Alias
: `has-notation`

Type
: `toggle`

Values
: Boolean, `true` or `false`.

Active value
: `true`.  

Example
: `?fq=has-notation:false`


#### Key signature

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=key-signature:"Some value"&fq=key-signature:"Some other value"&fb=key-signature:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `key-signature`

Type
: `select`

Values
: Any string value 

Default behaviour
: `union`

Default sort
: `count`


#### Time signature

For select facets, you can change the behaviour of the facet with the `fb` parameter, which takes the
alias and a value of either `intersection` or `union`. For example:
 
    ?fq=time-signature:"Some value"&fq=time-signature:"Some other value"&fb=time-signature:union

This would change the behaviour of the select facet to choose records with either the first or the second (a.k.a "OR")
rather than records with both values (a.k.a. "AND"). 

Alias
: `time-signature`

Type
: `select`

Values
: Any string value 

Default behaviour
: `union`

Default sort
: `count`



### Sorting

The available options for sorting results for the Incipits mode are:


#### Most relevant

Alias
: `relevance`



#### Alphabetical (Creator, A-Z)

Alias
: `alphabetical-creator`



#### Alphabetical (Title, A-Z)

Alias
: `alphabetical-title`



