import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from .. import codegen as cg


def setup(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    sub = subparsers.add_parser('gen', help='Generate hints for structured data (JSON, YAML)')
    sub.add_argument('-s', '--source', help="Path to structured data (JSON, YAML). "
                                            "If not specified, then the data will be read from stdin.")
    sub.set_defaults(func=main)
    return sub


def main(args: argparse.Namespace, out_channel=sys.stdout) -> None:
    """ $ typeit gen <source> <target>
    """
    try:
        with Path(args.source).open('r') as f:
            python_data = _read_data(f)
    except TypeError:
        # source is None, read from stdin
        python_data = _read_data(sys.stdin)

    typeit_schema = cg.typeit(python_data)
    python_src, __ = cg.codegen_py(typeit_schema)
    out_channel.write(python_src)
    out_channel.write('\n')


def _read_data(fd) -> Dict:
    buf = fd.read()  # because stdin does not support seek
    try:
        struct = json.loads(buf)
    except ValueError:
        try:
            import yaml
        except ImportError:
            raise RuntimeError(
                "Could not parse data as JSON, and could not locate PyYAML library "
                "to try to parse the data as YAML. You can either install PyYAML as a separate "
                "dependency, or use the `third_party` extra tag with typeit:\n\n"
                "$ pip install typeit[third_party]"
            )
        struct = yaml.full_load(buf)
    return struct
