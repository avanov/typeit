import pathlib as p
from typing import NamedTuple, Union, Dict

from typeit import TypeConstructor


def test_path():
    class X(NamedTuple):
        pure: p.PurePath
        pure_posix: p.PurePosixPath
        pure_win: p.PureWindowsPath
        path: p.Path
        # WinPath is not possible to instantiate on Linux,
        # we are omitting a test here
        posix_path: p.PosixPath

    mk_x, serialize_x = TypeConstructor(X)

    data = {
        'pure': '/',
        'pure_posix': '/a/b/c',
        'pure_win': '\\\\a\\b\\c',
        'path': '\\a\\b\\c',
        'posix_path': '.',
    }
    x = mk_x(data)
    assert serialize_x(x) == data


def test_path_union():
    class X(NamedTuple):
        x: p.Path | Dict

    mk_x, serialize_x = TypeConstructor(X)
    data = {
        'x': '/'
    }
    x = mk_x(data)
    assert isinstance(x.x, p.Path)
    assert serialize_x(x) == data

    data = {
        'x': {
            'x': '/'
        }
    }
    x = mk_x(data)
    assert isinstance(x.x, dict)
    assert serialize_x(x) == data
