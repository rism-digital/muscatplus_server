from urllib import parse

# Shamelessly copied from Django REST Framework:
#  https://github.com/encode/django-rest-framework/blob/master/rest_framework/utils/urls.py


def replace_query_param(url, key, val):
    """
    Given a URL and a key/val pair, set or replace an item in the query
    parameters of the URL, and return the new URL.
    """
    (scheme, netloc, path, query, fragment) = parse.urlsplit(url)
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict[key] = [val]
    query = parse.urlencode(
        sorted(query_dict.items()), doseq=True, quote_via=parse.quote
    )
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


def remove_query_param(url, key):
    """
    Given a URL and a key/val pair, remove an item in the query
    parameters of the URL, and return the new URL.
    """
    (scheme, netloc, path, query, fragment) = parse.urlsplit(url)
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict.pop(key, None)
    query = parse.urlencode(
        sorted(query_dict.items()), doseq=True, quote_via=parse.quote
    )
    return parse.urlunsplit((scheme, netloc, path, query, fragment))
