import json
from typing import NamedTuple, Optional

from typeit.custom_types import JsonString
from typeit import TypeConstructor


def test_json_string_direct_application():
    mk_js, serialize_js = TypeConstructor ^ JsonString[int]
    js = mk_js("5")
    assert isinstance(js, JsonString)
    assert js.data == 5
    assert serialize_js(js) == "5"


def test_json_string_structures():
    class Z(NamedTuple):
        z: int

    class X(NamedTuple):
        x: JsonString[str]
        y: JsonString[int]
        z: JsonString[Optional[Z]]

    mk_x, serialize_x = TypeConstructor ^ X

    data_x1 = dict(
        x=json.dumps("1"),
        y=json.dumps(2),
        z=json.dumps(None)
    )
    x1 = mk_x(data_x1)
    assert isinstance(x1, X)
    assert x1.x.data == "1"
    assert x1.y.data == 2
    assert x1.z.data is None
    assert serialize_x(x1) == data_x1

    data_x2 = dict(
        x=json.dumps("1"),
        y=json.dumps(2),
        z=json.dumps({'z': 3})
    )
    x2 = mk_x(data_x2)
    assert isinstance(x2.z.data, Z)
    assert x2.z.data.z == 3
    assert serialize_x(x2) == data_x2


def test_nested_json_string():
    class NestedOpt(NamedTuple):
        opt: JsonString[JsonString[Optional[int]]]

    mk_opt, serialize_opt = TypeConstructor ^ NestedOpt

    data_1 = dict(
        opt=json.dumps(json.dumps(None))
    )
    opt = mk_opt(data_1)
    assert isinstance(opt, NestedOpt)
    assert opt.opt.data.data is None
    assert serialize_opt(opt) == data_1

    data_2 = dict(
        opt=json.dumps(json.dumps(1))
    )
    opt = mk_opt(data_2)
    assert isinstance(opt, NestedOpt)
    assert opt.opt.data.data == 1
    assert serialize_opt(opt) == data_2


def test_nested_optional_json_string():
    class NestedOpt(NamedTuple):
        opt: JsonString[Optional[JsonString[Optional[int]]]]

    mk_opt, serialize_opt = TypeConstructor ^ NestedOpt

    data_1 = dict(
        opt=json.dumps(None)
    )
    opt1 = mk_opt(data_1)
    assert opt1.opt.data is None

    data_2 = dict(
        opt=json.dumps(json.dumps(1))
    )
    opt2 = mk_opt(data_2)
    assert isinstance(opt2, NestedOpt)
    assert opt2.opt.data is not None
    assert opt2.opt.data.data == 1
    assert serialize_opt(opt2) == data_2
