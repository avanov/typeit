import re
import keyword
from typing import Any, Type

NORMALIZATION_PREFIX = 'overridden__'


def normalize_name(name: str,
                   pattern=re.compile('^([_0-9]+).*$')) -> str:
    """ Some field name patterns are not allowed in NamedTuples
    https://docs.python.org/3.7/library/collections.html#collections.namedtuple
    """
    being_normalized = name.replace('-', '_').strip('_')
    if keyword.iskeyword(being_normalized) or pattern.match(being_normalized):
        return f'{NORMALIZATION_PREFIX}{being_normalized}'
    return being_normalized


def is_named_tuple(typ: Type[Any]) -> bool:
    return hasattr(typ, '_fields')


def clone_schema_node(node):
    """ Clonning the node and reassigning the same children,
    because clonning is recursive, but we are only interested
    in new version of the outermost schema node, the children nodes
    should be shared to avoid unnecessary duplicates.
    """
    new_node = node.clone()
    new_node.children = node.children
    return new_node