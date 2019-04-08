class _Flag: ...


# Disable strict matching of primitive types
# (for instance, allow '1' to be passed to a `x: int` attribute etc)
NON_STRICT_PRIMITIVES = _Flag()
