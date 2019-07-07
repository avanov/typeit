import typeit
from typeit.compat import PY_VERSION

if PY_VERSION >= (3, 7):
    from dataclasses import dataclass


    def test_dataclasses():

        @dataclass
        class InventoryItem:
            name: str
            unit_price: float
            quantity_on_hand: int = 0

        mk_inv, serialize_inv = typeit.type_constructor(InventoryItem)

        serialized = {
            'name': 'test',
            'unit_price': 1.0,
            'quantity_on_hand': 5,
        }
        x = mk_inv(serialized)
        assert isinstance(x, InventoryItem)
        assert serialize_inv(x) == serialized
