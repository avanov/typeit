import re
import keyword


def normalize_name(name: str,
                   pattern=re.compile('^([_0-9]+).*$')) -> str:
    """ Some field name patterns are not allowed in NamedTuples
    https://docs.python.org/3.7/library/collections.html#collections.namedtuple
    """
    being_normalized = name.replace('-', '_').strip('_')
    if keyword.iskeyword(being_normalized) or pattern.match(being_normalized):
        return f'{NORMALIZATION_PREFIX}{being_normalized}'
    return being_normalized


NORMALIZATION_PREFIX = 'overridden__'