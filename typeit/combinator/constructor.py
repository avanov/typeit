from functools import partial
from typing import Tuple, Callable, Dict, Any, Union, Type, Mapping, Sequence, ForwardRef

from pyrsistent import pmap
# this is different from pyrsistent.typing.PMap unfortunately
from pyrsistent import PMap as RealPMapType
from pyrsistent.typing import PMap

from .. import schema, flags
from ..custom_types.json_string import JsonStringSchema, JsonString
from ..definitions import OverridesT, NO_OVERRIDES
from ..parser import T, decide_node_type, OverrideT
from .combinator import Combinator
from ..schema import nodes

TypeTools = Tuple[ Callable[[Union[int, str, float, Sequence[Any], Mapping[str, Any]]], T]
                 , Callable[[T], Union[Sequence[Any], Mapping[str, Any]] ]]


class _TypeConstructor:
    def __init__(self, overrides: Union[Dict, OverridesT] = NO_OVERRIDES):
        self.overrides = pmap(overrides)
        self.memo: PMap[Type[Any], Union[nodes.SchemaNode, nodes.TupleSchema, nodes.SequenceSchema]] = pmap()

    def __call__(self,
        typ: Type[T],
        overrides: OverridesT = NO_OVERRIDES
    ) -> TypeTools:
        """ Generate a constructor and a serializer for the given type

        :param overrides: a mapping of type_field => serialized_field_name.
        """
        forward_refs = {}  # has to be mutable in the current implementation
        try:
            main_type_node, memo, forward_refs = decide_node_type(typ, overrides, self.memo, forward_refs)
        except TypeError as e:
            raise TypeError(
                f'Cannot create a type constructor for {typ}: {e}'
            ) from e
        else:
            # finalising forward references
            while True:
                unresolved = [r for r, v in forward_refs.items() if not v]
                if not unresolved:
                    break
                for ref in unresolved:
                    if ref.__forward_value__ is None:
                        forward_refs[ref] = main_type_node
                    else:
                        resolved_node, memo, forward_refs = decide_node_type(ref.__forward_value__, overrides, memo, forward_refs)
                        forward_refs[ref] = resolved_node

        self.memo = memo
        return (
            partial(schema.errors.errors_aware_constructor, main_type_node.deserialize),
            partial(schema.errors.errors_aware_constructor, main_type_node.serialize)
        )

    def __and__(self, override: OverrideT) -> '_TypeConstructor':
        combined = Combinator() & override

        overrides = pmap()
        for override in combined.combined:
            if isinstance(override, flags._Flag):
                upd = self.overrides.set(override, override.default_setting)

            elif isinstance(override, flags._ModifiedFlag):
                # override is a flag with extra settings
                upd = self.overrides.set(override[0], override[1])

            elif isinstance(override, schema.meta.TypeExtension):
                upd = self.overrides.set(override.typ, override)

            elif isinstance(override, (dict, RealPMapType)):
                # override is a field mapping
                upd = self.overrides.update(override)
            else:
                continue

            overrides = overrides.update(upd)

        return self.__class__(overrides=overrides)

    def __xor__(self, typ: Type[T]) -> TypeTools:
        return self.__call__(typ, self.overrides)

    # helper aliases for those who doesn't like combinators' syntax
    override = __and__
    apply_on = __xor__


type_constructor = _TypeConstructor() & JsonStringSchema[JsonString]
TypeConstructor = type_constructor
