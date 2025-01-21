from typing import Optional

from luqum.tree import SearchField
from luqum.visitor import TreeTransformer


class QueryTransformException(Exception):
    """
    Expected exceptions that may be raised while transforming the luqum tree
    """


class UnknownFieldInQueryException(QueryTransformException):
    pass


class AliasedSolrFieldTreeTransformer(TreeTransformer):
    """Takes a list of field aliases and their actual Solr fields
    and transforms the SearchField to replace the field name alias with
    the actual Solr field name.

    If `strict` is True then this class will raise an exception if the
    alias is not found in the field mapping. If it is False, then the name
    will simply be passed through as the Solr field.
    """

    def __init__(self, allowed_fields: dict[str, dict], strict: bool = True):
        super().__init__()
        self.allowed_fields = allowed_fields
        self.strict = strict

    def visit_search_field(self, node: SearchField, parents) -> SearchField:
        field_name: Optional[str] = self.allowed_fields.get(node.name)
        if field_name is None and self.strict:
            raise UnknownFieldInQueryException(f"Invalid field name {node.name}")

        node.name = field_name

        yield node
