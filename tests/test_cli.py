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
    with mock.patch('sys.stdin') as m_stdin:
        with mock.patch('sys.stdout') as m_stdout:
            with mock.patch('sys.exit') as m_exit:
                m_stdin.read.return_value = stdin_data
                main(['gen'])
                m_exit.assert_called_once_with(0)
                test_str = 'mk_main, dict_main = type_constructor(Main)'
                assert test_str in str(m_stdout.write.mock_calls[0])
