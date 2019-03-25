from typing import Iterator, NamedTuple, Any, Mapping, Union, Sequence, Optional
import re
import keyword
import colander
from . import interface as iface


NORMALIZATION_PREFIX = 'overridden__'


class InvalidData(NamedTuple):
    path: str
    reason: str
    sample: Optional[Any]


def normalize_name(name: str,
                   pattern=re.compile('^([_0-9]+).*$')) -> str:
    """ Some field name patterns are not allowed in NamedTuples
    https://docs.python.org/3.7/library/collections.html#collections.namedtuple
    """
    being_normalized = name.replace('-', '_').strip('_')
    if keyword.iskeyword(being_normalized) or pattern.match(being_normalized):
        return f'{NORMALIZATION_PREFIX}{being_normalized}'
    return being_normalized


def iter_invalid_data(error: colander.Invalid,
                      data: Mapping[str, Any]) -> Iterator[InvalidData]:
    """ A helper function to iterate over data samples that
    caused an exception at object construction. Use it like this:

    >>> try:
    >>>     obj = mk_obj(data)
    >>> except colander.Invalid as e:
    >>>     # iterate over a sequence of InvalidData
    >>>     for e in iter_invalid_data(e, data):
    >>>         ...

    """
    for e_path, msg in error.asdict().items():
        e_parts = []
        for x in e_path.split('.'):
            # x is either a list index or a dict key
            try:
                x = int(x)
            except ValueError:
                pass
            e_parts.append(x)
        # traverse data for a value that caused an error
        traversed_value: Union[None, iface.ITraversable] = data
        for i in e_parts:
            try:
                traversed_value = traversed_value[i]
            except KeyError:
                # handles the case when key is missing from payload
                traversed_value = None
                break
        yield InvalidData(path=e_path, reason=msg, sample=traversed_value)
