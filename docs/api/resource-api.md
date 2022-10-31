The Resource API provides data on individual source and authority records in RISM Online. Every resource has
a machine-processable JSON-LD representation with all the public data we have about that resource.

## Addresses and Identifiers

Most resource addresses you encounter in RISM Online are de-referenceable; that is, you can load them in an HTTP client,
such as a web browser, and it will return some representation of that resource. In addition, every address is also a
globally unique identifier for that resource. These addresses and identifiers are designed to be stable and cite-able 
references to all data that RISM publish.

## Using the Resource API

The JSON-LD response can be requested from the RISM Online server by passing an `Accept` header with 
`application/ld+json` as the value to the request. If you have access to the command-line `curl` tool:

    $ curl -H "Accept: application/ld+json" https://rism.online/sources/1001145660

Other tools, such as the [Talend API Tester](https://chrome.google.com/webstore/detail/talend-api-tester-free-ed/aejoelaoggembcahagimdiliamlcdmfm?hl=en) 
Google Chrome plugin provide a graphical interface to the API and the responses.

## Searching a resource

Person and Institution resources have a search interface that provide a pre-filtered view of the source records
related to them. This is an implementation of the [Search API](search-api.md), where the only supported mode is the
`source` mode, but where all the same filters and sorting mechanisms apply, and the response has the same structure.
This can be accessed by appending `/sources` to the URL of the resource URL:

    $ curl -H "Accept: application/ld+json" https://rism.online/people/51160/sources

Source resources have a similar interface, but they allow for searching the "contents" of a collection: Source records
that hold information about the individual contents of a source. This can be accessed by appending `/contents` to the
end of the resource URL:

    $ curl -H "Accept: application/ld+json" https://rism.online/sources/450060716/contents

## JSON-LD Expansion (Experimental)

JSON-LD can be parsed just like JSON. However, with some additional processing of the context document, the JSON may be
transformed into Linked Data triples. This is currently work in progress.
