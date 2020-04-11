import typeit
from typeit.compat import PY_VERSION

if PY_VERSION >= (3, 7):
    from dataclasses import dataclass


    def test_dataclasses():

        @dataclass
        class InventoryItem:
            name: str
            unit_price: float
            quantity_on_hand: int

        overrides = {
            (InventoryItem, 'quantity_on_hand'): 'quantity'
        }

        mk_inv, serialize_inv = typeit.TypeConstructor.override(overrides).apply_on(InventoryItem)

        serialized = {
            'name': 'test',
            'unit_price': 1.0,
            'quantity': 5,
        }
        x = mk_inv(serialized)
        assert isinstance(x, InventoryItem)
        assert serialize_inv(x) == serialized

    def test_with_default_values():

        @dataclass
        class X:
            one: int
            two: int = 2
            three: int = 3

        data = {'one': 1}

        mk_x, serialize_x = typeit.TypeConstructor ^ X
        x = mk_x(data)
        assert serialize_x(x) == {'one': 1, 'two': 2, 'three': 3}
