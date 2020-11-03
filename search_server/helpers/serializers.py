import operator
from typing import Dict, List, Union
import serpy


def _remove_none(d: Dict) -> Dict:
    return {k: v for k, v in d.items() if v is not None}


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

    def to_value(self, instance: Dict) -> Union[Dict, List]:
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
