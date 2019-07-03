from typing import Any, Mapping, Type, Sequence

from typing_extensions import Protocol


class ITraversable(Protocol):
    def __getitem__(self, item: Any):
        ...


class IType(Protocol):
    __name__: str
    __class__: Type
    __args__: Sequence
    _fields: Sequence[str]

    def _asdict(self) -> Mapping[str, Any]:
        ...


class INamedTuple(Protocol):
    _name: str
