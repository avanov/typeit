import io

import pytest
from unittest import mock
from typeit.cli import main


@pytest.mark.parametrize("stdin_data", [
    """{"x": "Hello", "y": "World", "z": {"a": 1}}""",
    """
    x: Hello
    y: World
    z:
      a: 1
    """
])
def test_cli(stdin_data):
    out_channel = io.StringIO()
    with mock.patch('sys.stdin') as m_stdin:
        with mock.patch('sys.exit') as m_exit:
            m_stdin.read.return_value = stdin_data
            main(['gen'], stdout=out_channel)
            m_exit.assert_called_once_with(0)
            test_str = 'mk_main, serialize_main = type_constructor ^ Main'
            out_channel.seek(0)
            code_snippet = str(out_channel.read())
            assert test_str in code_snippet
