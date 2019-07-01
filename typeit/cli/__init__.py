""" Place for Console Scripts.
"""
import argparse
import sys

from pkg_resources import get_distribution

from . import gen


def main(args=None, stdout=sys.stdout):
    parser = argparse.ArgumentParser(description='Type it!')
    parser.add_argument('-V', '--version', action='version',
                        version='typeit {}'.format(get_distribution("typeit").version))
    subparsers = parser.add_subparsers(title='sub-commands',
                                       description='valid sub-commands',
                                       help='additional help',
                                       dest='sub-command')
    # make subparsers required (see http://stackoverflow.com/a/23354355/458106)
    subparsers.required = True

    # $ typeit gen
    # ---------------------------
    gen.setup(subparsers)

    # Parse arguments and config
    # --------------------------
    if args is None:
        args = sys.argv[1:]
    args = parser.parse_args(args)

    # Set up and run
    # --------------
    args.func(args, out_channel=stdout)
    sys.exit(0)
