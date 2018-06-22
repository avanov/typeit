from .parser import type_constructor as construct, parse as typeit


type_constructor = lambda x: construct(x).deserialize


__all__ = ['type_constructor', 'typeit']