import pathlib as p
from typing import NamedTuple

from typeit import type_constructor


class X(NamedTuple):
    pure: p.PurePath
    pure_posix: p.PurePosixPath
    pure_win: p.PureWindowsPath
    path: p.Path
    # WinPath is not possible to instantiate on Linux,
    # we are omitting a test here
    posix_path: p.PosixPath


mk_x, dict_x = type_constructor(X)


def test_path():
    data = {
        'pure': '/',
        'pure_posix': '/a/b/c',
        'pure_win': '\\\\a\\b\\c',
        'path': '\\a\\b\\c',
        'posix_path': '.',
    }
    x = mk_x(data)
    assert dict_x(x) == data
