from money.money import Money

import typeit


def test_regular_classes():

    mk_x, serialize_x = typeit.TypeConstructor & typeit.flags.NonStrictPrimitives ^ Money

    serialized = {
        'amount': '10',
        'currency': 'GBP',
    }

    x = mk_x(serialized)
    assert isinstance(x, Money)
    assert serialize_x(x) == serialized
