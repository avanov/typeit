import argparse
import json
import sys
from pathlib import Path

from .. import parser


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
            struct = json.load(f)
    except TypeError:
        # source is None, read from stdin
        struct = json.load(sys.stdin)

    struct = parser.construct_type('main', parser.parse(struct))
    sys.stdout.write(parser.codegen(struct))
    sys.stdout.write('\n')
    sys.exit(0)
