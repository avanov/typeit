from json import loads
from typing import Union, Sequence, Mapping
from typeit import TypeConstructor


JSONValue = Union[ None
                 , str
                 , float
                 , bool
                 , int
                 , Sequence['JSONValue']
                 , Mapping[str, 'JSONValue']
                 ]


def test_forward_refs():
    parse, dump = TypeConstructor ^ JSONValue

    assert isinstance(parse(loads("1")), int)
    assert isinstance(parse(loads("1.0")), float)
    assert isinstance(parse(loads('"1.0"')), str)
    assert isinstance(parse(loads('{"data": "1.0"}')), dict)
    assert isinstance(parse(loads('{"data": "1.0"}'))['data'], str)
    assert isinstance(parse(loads('[["1.0"]]')), list)
    assert isinstance(parse(loads('[["1.0"]]'))[0], list)
    assert isinstance(parse(loads('[["1.0"]]'))[0][0], str)
    assert isinstance(parse(loads('[{"data": 1.0}]'))[0], dict)
    assert isinstance(parse(loads('[{"data": 1.0}]'))[0]['data'], float)
