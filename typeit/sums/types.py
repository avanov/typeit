from .impl import SumType


class Either(SumType):
    class Left: ...

    class Right: ...


class Maybe(SumType):
    class Just: ...

    class Nothing: ...
