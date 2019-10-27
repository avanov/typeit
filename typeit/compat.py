import sys

PY_VERSION = sys.version_info[:2]
PY37 = PY_VERSION == (3, 7)
PY36 = PY_VERSION == (3, 6)

if PY_VERSION < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal


__all__ = ('PY_VERSION', 'PY37', 'PY36', 'Literal')
