# RISM Online API

The RISM Online API can be used to retrieve machine-readable representations of all available resources
in the RISM data. Every URL has both human-readable and a machine-readable representation, and these
may be changed by adjusting the `Accept` HTTP request header; a technique known as "Content Negotiation".

By default, the RISM Online service will deliver HTML-based representations of the content, suitable for the
majority of our users to browse and use the website. Under the hood, your browser is sending an `Accept` header
of `text/html`, which signals to our server that it should respond with the HTML version of a particular URL.

If we change the value of the `Accept` header to ask for a JSON representation using `application/ld+json`, 
the server will respond with a more machine-friendly representation of the same data in JSON-LD format.

Any standard HTTP client will have the facilities to do this. If you have the `curl` command available through the
command-line terminal in your local machine, you can experiment with this very easily.

    $ curl -H "Accept: application/ld+json" https://rism.online/sources/1001145660

This will return a response containing JSON-LD. If you vary this with:

    $ curl -H "Accept: text/html" https://rism.online/sources/1001145660

You will get an HTML response.

> Note: The HTML response you receive will not be suitable for "scraping"
> the page for information. When the HTML page loads it runs our 
> User Interface web application, which in turn performs a JSON request to
> retrieve the data from the API and update the page dynamically. If you load the page
> in your browser, this process is transparent to the user, but if you load the HTML page from the API
> you will only retrieve an unfilled template response.
