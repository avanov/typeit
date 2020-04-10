from typing import NamedTuple

import pytest

import typeit as tt
import inflection


def test_combinators():
    flags = tt.flags.NonStrictPrimitives & tt.flags.NonStrictPrimitives()
    flags = flags & tt.flags.SumTypeDict('_type')
    flags = flags & 1
    x = tt.TypeConstructor & flags

    # test aliases
    construct, to_serializable = tt.TypeConstructor\
        .override(tt.flags.NonStrictPrimitives)\
        .override(tt.flags.NonStrictPrimitives())\
        .override(tt.flags.SumTypeDict('_type'))\
        .apply_on(int)


@pytest.mark.parametrize('modifier, expected_dict', [
    (
        lambda x: x,
        {
            'field_one': 'one',
            'field_two': {'field_three': 'three'}
        }
    ),
    (
        lambda x: f'prefixed-{x}',
        {
            'prefixed-field_one': 'one',
            'prefixed-field_two': {'prefixed-field_three': 'three'}
        }
    ),
    (
            inflection.camelize,
            {
                'FieldOne': 'one',
                'FieldTwo': {'FieldThree': 'three'},
            }
    ),
    (
        lambda x: inflection.camelize(x, uppercase_first_letter=False),
        {
            'fieldOne': 'one',
            'fieldTwo': {'fieldThree': 'three'},
        }
    ),
])
def test_global_names_override(modifier, expected_dict):
    flags = tt.flags.GlobalNameOverride(modifier)
    Constructor = tt.TypeConstructor & flags

    class FoldedData(NamedTuple):
        field_three: str

    class Data(NamedTuple):
        field_one: str
        field_two: FoldedData

    constructor, to_serializable = Constructor ^ Data

    data = Data(field_one='one',
                field_two=FoldedData(field_three='three'))

    serialized = to_serializable(data)
    assert serialized == expected_dict

    constructed = constructor(serialized)
    assert constructed == data
