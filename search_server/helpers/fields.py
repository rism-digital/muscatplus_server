from typing import Any, Dict, Optional, List
import serpy


class StaticField(serpy.Field):
    """
    A serpy field that simply repeats a static value.
    """
    def __init__(self, value, *args, **kwargs) -> None:
        super(StaticField, self).__init__(*args, **kwargs)
        self.value = value

    def to_value(self, value) -> Any:
        return self.value

    def as_getter(self, serializer_field_name, serializer_cls) -> Any:
        return self.to_value


class LanguageMapField(serpy.Field):
    def to_value(self, value: Any) -> Dict[str, List]:
        return {"none": [value]}
