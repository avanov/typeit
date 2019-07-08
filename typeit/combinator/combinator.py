from itertools import chain
from typing import NamedTuple, Any

from pyrsistent import pvector
from pyrsistent.typing import PVector


class Combinator(NamedTuple):
    combined: PVector[Any] = pvector()

    def __and__(self, other: Any) -> 'Combinator':
        if isinstance(other, Combinator):
            cmb = other.combined
        else:
            cmb = [other]
        return self._replace(combined=pvector(chain(self.combined, cmb)))
