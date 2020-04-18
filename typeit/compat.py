import sys

PY_VERSION = sys.version_info[:2]

if PY_VERSION < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal


__all__ = ('PY_VERSION', 'Literal')
