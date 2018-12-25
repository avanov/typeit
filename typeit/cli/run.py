import argparse
import json
import yaml
import sys
from pathlib import Path

from .. import codegen as cg


def setup(subparsers):
    sub = subparsers.add_parser('gen', help='Generate hints for structured data (JSON, YAML)')
    sub.add_argument('-s', '--source', help="Path to structured data (JSON, YAML). "
                                            "If not specified, then the data will be read from stdin.")
    sub.set_defaults(func=main)
    return sub


def main(args: argparse.Namespace):
    """ $ typeit gen <source> <target>
    """
    try:
        with Path(args.source).open('r') as f:
            struct = _read_data(f)
    except TypeError:
        # source is None, read from stdin
        struct = _read_data(sys.stdin)

    struct, overrides = cg.typeit(struct)
    python_src, __ = cg.codegen_py(struct, overrides)
    sys.stdout.write(python_src)
    sys.stdout.write('\n')
    sys.exit(0)


def _read_data(fd):
    buf = fd.read()  # because stdin does not support seek
    try:
        struct = json.loads(buf)
    except ValueError:
        struct = yaml.load(buf)
    return struct
