import io

import pytest
from unittest import mock
from typeit.cli import main


TYPE_REF = 'mk_main, serialize_main = type_constructor ^ Main'

@pytest.mark.parametrize("stdin_data, reference_snippet", [
    ("""{"x": "Hello", "y": "World", "z": {"a": 1}}""", TYPE_REF),
    ("""
    x: Hello
    y: World
    z:
      a: 1
    """, TYPE_REF),
    ("""1""", "mk_int, serialize_int = type_constructor ^ int"),
    ("""1.0""", "mk_float, serialize_float = type_constructor ^ float"),
    (''' "1" ''', "mk_str, serialize_str = type_constructor ^ str"),
    (''' true ''', "mk_bool, serialize_bool = type_constructor ^ bool"),
    (''' null ''', "mk_none, serialize_none = type_constructor ^ None"),
    (''' [] ''', "Main = Sequence[Any]\n\n\nmk_main, serialize_main = type_constructor ^ Main"),
    (''' [[]] ''', "Main = Sequence[Sequence[Any]]\n\n\nmk_main, serialize_main = type_constructor ^ Main"),
    (''' [[1]] ''', "Main = Sequence[Sequence[int]]\n\n\nmk_main, serialize_main = type_constructor ^ Main"),
    (''' [[ {"x": {"y": null}} ]] ''', "class Main(NamedTuple):\n    x: X\n\n\nmk_main, serialize_main = type_constructor ^ Main"),
])
def test_cli(stdin_data, reference_snippet):
    out_channel = io.StringIO()
    with mock.patch('sys.stdin') as m_stdin:
        with mock.patch('sys.exit') as m_exit:
            m_stdin.read.return_value = stdin_data
            main(['gen'], stdout=out_channel)
            m_exit.assert_called_once_with(0)
            out_channel.seek(0)
            code_snippet = str(out_channel.read())
            assert reference_snippet in code_snippet
