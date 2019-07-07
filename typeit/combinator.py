from functools import partial
from typing import Tuple, Callable, Dict, Any, Union, List, Type

from pyrsistent import pmap

from . import flags, schema
from .definitions import OverridesT, NO_OVERRIDES
from .parser import T, decide_node_type, OverrideT
from .schema.errors import errors_aware_constructor

TypeTools = Tuple[ Callable[[Dict[str, Any]], T]
                 , Callable[[T], Union[List, Dict]] ]


class _TypeConstructor:
    def __init__(self, overrides: Union[Dict, OverridesT] = NO_OVERRIDES):
        self.overrides = pmap(overrides)
        self.memo = pmap()

    def __call__(self,
        typ: Type[T],
        overrides: OverridesT = NO_OVERRIDES
    ) -> TypeTools:
        """ Generate a constructor and a serializer for the given type

        :param overrides: a mapping of type_field => serialized_field_name.
        """
        try:
            schema_node, memo = decide_node_type(typ, overrides, self.memo)
        except TypeError as e:
            raise TypeError(
                f'Cannot create a type constructor for {typ}: {e}'
            )
        self.memo = memo
        return (
            partial(errors_aware_constructor, schema_node.deserialize),
            partial(errors_aware_constructor, schema_node.serialize)
        )

    def __and__(self, override: OverrideT) -> '_TypeConstructor':
        if isinstance(override, flags._Flag):
            overrides = self.overrides.set(override, override.default_setting)

        elif isinstance(override, schema.meta.TypeExtension):
            overrides = self.overrides.set(override.typ, override)

        elif isinstance(override, tuple):
            # override is a flag with extra settings
            overrides = self.overrides.set(override[0], override[1])

        else:
            # override is a field mapping
            overrides = self.overrides.update(override)

        return self.__class__(overrides=overrides)

    def __xor__(self, typ: Type[T]) -> TypeTools:
        return self.__call__(typ, self.overrides)


type_constructor = _TypeConstructor()