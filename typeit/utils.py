import re
from typing import Tuple


def normalize_name(name: str,
                   pattern=re.compile('^([_0-9]+).*$')) -> Tuple[str, bool]:
    """ Some field name patterns are not allowed in NamedTuples
    https://docs.python.org/3.7/library/collections.html#collections.namedtuple
    """
    if name in RESERVED_WORDS or pattern.match(name):
        return f'{NORMALIZATION_PREFIX}{name}', True
    return name, False


def denormalize_name(name: str) -> Tuple[str, bool]:
    """ Undo normalize_name()
    """
    if name in NORMALIZED_RESERVED_WORDS or name.startswith(NORMALIZATION_PREFIX):
        return name[len(NORMALIZATION_PREFIX):], True
    return name, False


NORMALIZATION_PREFIX = 'normalized__'


RESERVED_WORDS = {
    'and', 'del', 'from',
    'not', 'while','as',
    'elif', 'global', 'or',
    'with','assert', 'else',
    'if', 'pass', 'yield',
    'break', 'except', 'import',
    'print', 'class', 'exec',
    'in', 'raise', 'continue',
    'finally', 'is', 'return',
    'def', 'for', 'lambda', 'try',
}


NORMALIZED_RESERVED_WORDS = {
    f'{NORMALIZATION_PREFIX}{x}' for x in RESERVED_WORDS
}