from typing import Union, Optional

import serpy

from shared_helpers.identifiers import get_identifier, RISM_JSONLD_CONTEXT


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


class JSONLDDictSerializer(serpy.DictSerializer):
    """
    Automatically applies the lookup to add the JSON-LD Context to the result. Serializes a dictionary
    """
    ctx = serpy.MethodField(
        label="@context"
    )

    def get_ctx(self, obj) -> Optional[dict]:
        direct_request: bool = self.context.get("direct_request", False)
        return get_jsonld_context(self.context.get("request")) if direct_request else None


class JSONLDSerializer(serpy.Serializer):
    ctx = serpy.MethodField(
        label="@context"
    )

    def get_ctx(self, obj) -> Optional[dict]:
        direct_request: bool = self.context.get("direct_request", False)
        return get_jsonld_context(self.context.get("request")) if direct_request else None


class JSONLDAsyncDictSerializer(serpy.AsyncDictSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )

    def get_ctx(self, obj) -> Optional[dict]:
        direct_request: bool = self.context.get("direct_request", False)
        return get_jsonld_context(self.context.get("request")) if direct_request else None


class JSONLDAsyncSerializer(serpy.AsyncSerializer):
    ctx = serpy.MethodField(
        label="@context"
    )

    def get_ctx(self, obj) -> Optional[dict]:
        direct_request: bool = self.context.get("direct_request", False)
        return get_jsonld_context(self.context.get("request")) if direct_request else None
