import re
import keyword
import string
from typing import Any, Type, TypeVar, Callable

from colander import TupleSchema, SequenceSchema

from typeit import flags
from typeit.definitions import OverridesT
from typeit.schema.nodes import SchemaNode

NORMALIZATION_PREFIX = 'overridden__'
SUPPORTED_CHARS = string.ascii_letters + string.digits


T = TypeVar('T', SchemaNode, TupleSchema, SequenceSchema)


def normalize_name(name: str,
                   pattern=re.compile('^([_0-9]+).*$')) -> str:
    """ Some field name patterns are not allowed in NamedTuples
    https://docs.python.org/3.7/library/collections.html#collections.namedtuple
    """
    being_normalized = name
    if not being_normalized.isidentifier():
        being_normalized = ''.join([
            c if c in SUPPORTED_CHARS else '_' for c in being_normalized
        ])
    being_normalized = being_normalized.strip('_')

    if keyword.iskeyword(being_normalized) or pattern.match(being_normalized):
        return f'{NORMALIZATION_PREFIX}{being_normalized}'
    return being_normalized


def is_named_tuple(typ: Type[Any]) -> bool:
    return hasattr(typ, '_fields')


def clone_schema_node(node: T) -> T:
    """ Clonning the node and reassigning the same children,
    because clonning is recursive, but we are only interested
    in a new version of the outermost schema node, the children nodes
    should be shared to avoid unnecessary duplicates.
    """
    new_node = node.clone()
    # a list comprehension to place the same nodes into
    # a new wrapping list object, so that extending
    # the cloned node with new children doesn't affect the original node
    new_node.children = [x for x in node.children]
    return new_node


def get_global_name_overrider(overrides: OverridesT) -> Callable[[str], str]:
    return overrides.get(flags.GlobalNameOverride, flags.Identity)
