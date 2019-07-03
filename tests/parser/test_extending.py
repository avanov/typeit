from typing import NamedTuple, Optional

from money.currency import Currency
from money.money import Money

import typeit
from typeit import schema, parser as p


def test_extending():
    class X(NamedTuple):
        x: Money

    class MoneySchema(schema.types.Tuple):
        def deserialize(self, node, cstruct):
            r = super().deserialize(node, cstruct)
            if r in (schema.types.Null, None):
                return r
            try:
                currency = Currency(r[0])
            except ValueError:
                raise typeit.Invalid(node, f'Invalid currency token in {r}', cstruct)

            try:
                rv = Money(r[1], currency)
            except:
                raise typeit.Invalid(node, f'Invalid amount in {r}', cstruct)

            return rv

        def serialize(self, node, appstruct: Optional[Money]):
            if appstruct is None or appstruct is schema.types.Null:
            # if appstruct is None or appstruct is schema.types.Null:
                return appstruct

            r = (appstruct.currency, appstruct.amount)
            return super().serialize(node, r)

    mk_x, serialize_x = (
        p.type_constructor
            & MoneySchema[Money] << schema.types.Enum(Currency) << schema.primitives.NonStrictStr()
            ^ X
    )

    serialized = {
        'x': ('GBP', '10')
    }

    x = mk_x(serialized)
    assert isinstance(x.x, Money)
    assert serialize_x(x) == serialized
