import operator
from typing import Union, Optional
import serpy

from search_server.helpers.identifiers import get_identifier, RISM_JSONLD_CONTEXT


def _remove_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


# A type that represents the fact that the JSON-LD context can be given either by URI or an embedded context object.
JSONLDContext = Union[str, dict]


def get_jsonld_context(request) -> JSONLDContext:
    """
    Returns the configured JSON-LD context string. If the `context_uri` setting is
    set to True in the server configuration file, this will return the URI for the
    "context" handler. If it is set to False, it will return the full JSON-LD Context
    object inline.

    :param request: A Sanic request object, with the 'app.context_uri' setting added to it during applicaton startup.
    :return: Either a string representing the URI to the context object, or the context object itself as a Dictionary.
    """
    if request.app.ctx.context_uri:
        return get_identifier(request, "context")

    return RISM_JSONLD_CONTEXT["@context"]


class ContextSerializer(serpy.Serializer):
    """
        Used for passing along context settings for serializing objects.
        This is useful for passing request data down serializer
        chains to provide, for example, information about the current request
        to the serialized output.
    """
    def __init__(self, *args, **kwargs) -> None:
        super(ContextSerializer, self).__init__(*args, **kwargs)

        if 'context' in kwargs:
            self.context = kwargs['context']

    def to_value(self, instance: dict) -> Union[dict, list]:
        """
        Filters out values that have been serialized to 'None' to prevent
        them from being sent to the browser.

        :param instance: An object to be serialized
        :return: A filtered dictionary or a list of filtered dictionaries.
        """
        v = super().to_value(instance)

        if self.many:
            return [_remove_none(d) for d in v]

        return _remove_none(v)


class ContextDictSerializer(ContextSerializer):
    """
    Used for serializing dictionaries instead of Python objects.
    Simply overrides the `getter` to operate on a dictionary.
    """
    default_getter = operator.itemgetter


class JSONLDContextDictSerializer(ContextDictSerializer):
    """
    Automatically applies the lookup to add the JSON-LD Context to the result. Serializes a dictionary
    """
    ctx = serpy.MethodField(
        label="@context"
    )

    def get_ctx(self, obj) -> Optional[dict]:
        direct_request: bool = self.context.get("direct_request", False)
        return get_jsonld_context(self.context.get("request")) if direct_request else None


class JSONLDContextSerializer(ContextSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )

    def get_ctx(self, obj) -> Optional[dict]:
        direct_request: bool = self.context.get("direct_request", False)
        return get_jsonld_context(self.context.get("request")) if direct_request else None
