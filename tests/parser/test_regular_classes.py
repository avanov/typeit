from money.money import Money

import typeit


def test_regular_classes():

    mk_x, serialize_x = typeit.type_constructor & typeit.flags.NON_STRICT_PRIMITIVES ^ Money

    serialized = {
        'amount': '10',
        'currency': 'GBP',
    }

    x = mk_x(serialized)
    assert isinstance(x, Money)
    assert serialize_x(x) == serialized
