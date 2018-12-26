from unittest import mock
from typeit.cli import main


def test_cli():
    with mock.patch('sys.stdin') as m_stdin:
        with mock.patch('sys.stdout') as m_stdout:
            with mock.patch('sys.exit') as m_exit:
                m_stdin.read.return_value = """
                    {"x": "Hello", "y": "World", "z": {"a": 1}}
                """
                main(['gen'])
                m_exit.assert_called_once_with(0)
                test_str = 'mk_main, dict_main = type_constructor(Main)'
                assert test_str in str(m_stdout.write.mock_calls[0])
