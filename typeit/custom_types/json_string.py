import json
from dataclasses import dataclass
from typing import Generic, TypeVar

from ..schema import Invalid
from ..schema.types import Structure


T = TypeVar('T')


@dataclass(frozen=True)
class JsonString(Generic[T]):
    data: T


class JsonStringSchema(Structure):
    def __init__(self, *args, json=json, **kwargs):
        super().__init__(*args, **kwargs)
        self.json = json

    def deserialize(self, node, cstruct: str) -> JsonString:
        """ Converts input string value ``cstruct`` to ``PortMapping``
        """
        try:
            data = self.json.loads(cstruct)
        except Exception as e:
            raise Invalid(node,
                f'Value is not a JSON string',
                cstruct
            ) from e
        return super().deserialize(node, {'data': data})

    def serialize(self, node, appstruct: JsonString) -> str:
        """ Converts ``PortMapping`` back to string value suitable for YAML config
        """
        serialized = super().serialize(node, appstruct)
        return self.json.dumps(serialized['data'])
