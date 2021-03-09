from typing import NamedTuple, Optional
import typeit
from typeit import flags
import inflection


def test_global_and_specific_overrides():
    class Item(NamedTuple):
        item_data: int


    class X(NamedTuple):
        x: int
        underscored_item: Optional[Item]


    overrides = {
        X.x: 'X',
        X.underscored_item: 'underscored_item',
        Item.item_data: 'item_data',
    }

    mk_x, serialize_x = typeit.TypeConstructor.override(overrides).override(
        flags.GlobalNameOverride(
            lambda x: inflection.camelize(x, uppercase_first_letter=False)
        )
    ).apply_on(X)

    data = {
        'X': 1,
        'underscored_item': {
            'item_data': 10
        }
    }

    mk_x(data)

