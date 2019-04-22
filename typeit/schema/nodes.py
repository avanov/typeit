import colander as col


class SchemaNode(col.SchemaNode):
    """ Colander's SchemaNode doesn't show node type in it's repr,
    we fix it with this subclass.
    """
    def __repr__(self) -> str:
        return f'SchemaNode({self.typ})'