from typing import NamedTuple, Optional, Any, Mapping, Iterator, Union, TypeVar, Callable

import colander

# Alias for typeit.Invalid, so users don't have to import two
# packages
from typeit import interface as iface

Invalid = colander.Invalid


class InvalidData(NamedTuple):
    path: str
    reason: str
    sample: Optional[Any]


class Error(ValueError):
    def __init__(self, validation_error, sample_data):
        super().__init__()
        self.validation_error = validation_error
        self.sample_data = sample_data

    def __iter__(self) -> Iterator[InvalidData]:
        return iter_invalid(self.validation_error, self.sample_data)

    def __str__(self):
        return str(self.validation_error)


def iter_invalid(error: Invalid,
                 data: Mapping[str, Any]) -> Iterator[InvalidData]:
    """ A helper function to iterate over data samples that
    caused an exception at object construction. Use it like this:

    >>> try:
    >>>     obj = mk_obj(data)
    >>> except Invalid as e:
    >>>     # iterate over a sequence of InvalidData
    >>>     for e in iter_invalid(e, data):
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
            # root object is always an empty string,
            # it may happen with type_constructor ^ <python built-in type>
            if not i:
                break
            try:
                traversed_value = traversed_value[i]
            except (KeyError, TypeError):
                # type error may happen when namedtuple is accessed
                # as a tuple but the index is a string value
                try:
                    traversed_value = getattr(traversed_value, i)
                except AttributeError:
                    # handles the case when key is missing from payload
                    traversed_value = None
                    break
        yield InvalidData(path=e_path, reason=msg, sample=traversed_value)


T = TypeVar('T')
S = TypeVar('S')


def errors_aware_constructor(construct: Callable[[T], S], data: T) -> S:
    try:
        return construct(data)
    except Invalid as e:
        raise Error(validation_error=e,
                    sample_data=data) from e
