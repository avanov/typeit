import typeit as tt

def test_combinators():
    flags = tt.flags.NON_STRICT_PRIMITIVES & tt.flags.NON_STRICT_PRIMITIVES
    flags = flags & tt.flags.SUM_TYPE_DICT << '_type'
    flags = flags & 1
    x = tt.type_constructor & flags