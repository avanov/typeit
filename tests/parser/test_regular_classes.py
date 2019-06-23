from money.money import Money

from typeit import parser as p
from typeit import flags


def test_regular_classes():

    mk_x, dict_x = p.type_constructor & flags.NON_STRICT_PRIMITIVES ^ Money

    serialized = {
        'amount': '10',
        'currency': 'GBP',
    }

    x = mk_x(serialized)
    assert isinstance(x, Money)
    assert dict_x(x) == serialized