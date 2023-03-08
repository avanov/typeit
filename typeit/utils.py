import re
import keyword
import string
import inspect as ins
from typing import Any, Type, TypeVar, Callable, Optional

from colander import TupleSchema, SequenceSchema

from typeit import flags
from typeit.definitions import OverridesT
from typeit.parser import get_type_attribute_info
from typeit.schema.nodes import SchemaNode

NORMALIZATION_PREFIX = 'overridden__'
SUPPORTED_CHARS = string.ascii_letters + string.digits


T = TypeVar('T', SchemaNode, TupleSchema, SequenceSchema)
A = TypeVar('A')
B = TypeVar('B')

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


def new(t: Type[A], scope: Optional[B] = None) -> A:
    """Experimental: Init a type instance from the values of the provided scope, as long as the scope variables
    have the same names and their types match the types of the attributes being initialised.
    """
    if scope is None:
        f = ins.currentframe().f_back.f_locals
    else:
        f_ = scope.__annotations__
        f = {x: getattr(scope, x) for x in f_}

    tattrs = get_type_attribute_info(t)
    constr = {}
    for attr in tattrs:
        if attr.name not in f:
            raise AttributeError(f"Could not find attribute {attr.name} for type {t.__class__} in the provided context")
        ctxval = f[attr.name]
        if not isinstance(ctxval, attr.resolved_type):
            raise AttributeError(f"Types do not match: '{attr.name}' has to be {attr.resolved_type} but got {type(ctxval)} instead.")
        constr[attr.name] = ctxval
    return t(**constr)
