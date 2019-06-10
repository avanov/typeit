import re
from typing import Dict, Any, get_type_hints, Type, Iterator, Set, NamedTuple


SUM_TYPE_VARIANT_NAME_RE = re.compile('^[A-Z][0-9A-Za-z_]*$')


class SumTypeMetaData:
    __slots__ = ('type', 'variants', 'values')

    def __init__(self,
                 type,
                 variants: Dict[str, 'SumType'],
                 values: Dict[str, str]) -> None:
        self.type = type
        self.variants = variants
        self.values = values


class VariantMeta(NamedTuple):
     variant_of: Any
     variant_name: Any
     constructor: Any
     value: Any


class SumTypeMetaclass(type):
    """ Metaclass object to be used with the actual SumType implementation.
    """
    # This hack is copied from python's standard enum.Enum implementation:
    # ------------
    # Dummy value for SumType as SumTypeMetaclass explicitly checks for it,
    # but of course until SumTypeMetaclass finishes running the first time
    # the SumType class doesn't exist.
    __sum_type_base = None

    def __new__(mcs, class_name: str, bases, attrs: Dict[str, Any]):
        """ This magic method is called when a new SumType class is being defined and parsed.

        :param attrs: all definitions inside a new type scope represented as a key-value map
        """
        # type constructor
        user_defined_sum_class: Type = type.__new__(mcs, class_name, bases, attrs)
        if mcs.__sum_type_base is None:
            # the first call finalizes the SumType class itself, an all subsequent
            # calls are user-defined sum types.
            mcs.__sum_type_base = user_defined_sum_class
            return user_defined_sum_class

        is_user_defined_base = mcs.__sum_type_base not in bases
        variants = {}
        variant_values = {}

        # 1. Populating variants from short-form definitions:
        #    class A(SumType):
        #        B: type
        # --------------------------------------------------
        # note that the value will be a lower-case version of the variant name
        data_constructors = (
            x for x in attrs.items()
            if SUM_TYPE_VARIANT_NAME_RE.match(x[0])
        )

        for variant_name, data_constructor in data_constructors:
            if variant_name in variants:
                raise TypeError(f'Variant {variant_name} is already defined for {class_name}')

            # data constructor
            data_constructor_hints = get_type_hints(data_constructor)
            if data_constructor_hints:
                data_constructor = NamedTuple(variant_name, data_constructor_hints.items())
            else:
                data_constructor = data_constructor.__bases__[0]
                if data_constructor is object:
                    data_constructor = NamedTuple(variant_name, ())

            value = variant_name.lower()
            # necessary for ``type(SumType.X) is SumType``
            variant = object.__new__(user_defined_sum_class)
            variant.__init__(
                variant_meta=VariantMeta(
                    variant_of=user_defined_sum_class,
                    variant_name=variant_name,
                    constructor=data_constructor,
                    value=value,
                )
            )

            setattr(user_defined_sum_class, variant_name, variant)
            variants[variant_name] = variant
            variant_values[value] = variant_name

        if is_user_defined_base:
            verify_consistency(bases[0].__sum_meta__.variants, variants)

        # 2. Finalize
        # --------------------------------------------------
        user_defined_sum_class.__sum_meta__ = SumTypeMetaData(
            type=user_defined_sum_class,
            # set of SumType variants
            variants=variants,
            # dict of value => variant mappings
            values=variant_values
        )

        # 3. Hacks to mimic Enum interface
        # --------------------------------------------------
        # 3.1 This hack is copied from python's standard enum.Enum implementation:
        # replace any other __new__ with our own (as long as SumType is not None,
        # anyway) -- again, this is to support pickle
        user_defined_sum_class.__new__ = mcs.__sum_type_base.__new__
        return user_defined_sum_class

    # Make the object iterable, similar to the standard enum.Enum
    def __iter__(cls) -> Iterator:
        return cls.__sum_meta__.variants.values().__iter__()

    def __call__(cls, value):
        """Either returns an existing member, or creates a new SumType class.
        """
        # simple value lookup
        return cls.__new__(cls, value)


class SumType(metaclass=SumTypeMetaclass):
    __sum_meta__: SumTypeMetaData = None

    def __instancecheck__(self, other) -> bool:
        try:
            m1 = self.__variant_meta__
            m2 = other.__variant_meta__
        except AttributeError:
            return False

        if not issubclass(m2.variant_of, self.__class__):
            return False

        return m1.variant_name == m2.variant_name

    @classmethod
    def values(cls) -> Set:
        return set(cls.__sum_meta__.values.keys())

    def __init__(self,
                 variant_meta: VariantMeta,
                 data_args=None,
                 data_kwargs=None) -> None:
        """
        :param variant_of: class of the SumType this variant instance belongs to
        :param name: name of the variant, as it is defined in the source code (uppercase)
        :param value: variant value
        :param constructor: constructor for a data that this variant can hold
        """
        self.__variant_meta__ = variant_meta
        if data_args or data_kwargs:
            data = variant_meta.constructor(*data_args, **data_kwargs)
            self.__getattribute__ = data.__getattribute__

    def __getattr__(self, item):
        return self.__getattribute__(item)

    def __call__(self, *data_args, **data_kwargs) -> 'SumType':
        """ Returns a data-holding variant"""
        instance = object.__new__(self.__sum_meta__.type)
        instance.__init__(
            variant_meta=self.__variant_meta__,
            data_args=data_args,
            data_kwargs=data_kwargs,
        )
        return instance

    def __eq__(self, other: 'SumType') -> bool:
        """ This method is redefined only to simplify variant comparison for tests with mocks that
        might do things like mocked_function.assert_called_with(SumType.VARIANT)
        """
        try:
            return self.__variant_meta__ == other.__variant_meta__
        except AttributeError:
            return False

    # https://docs.python.org/3/reference/datamodel.html#object.__hash__
    # If a class that overrides __eq__() needs to retain the implementation of __hash__() from a parent class,
    # the interpreter must be told this explicitly by setting __hash__ = <ParentClass>.__hash__
    __hash__ = object.__hash__

    def __repr__(self) -> str:
        return (
            f'SumType(type={self.__variant_meta__.variant_of.__module__}.'
            f'{self.__variant_meta__.variant_of.__name__}, '
            f'name={self.__variant_meta__.variant_name}'
        )

    def __new__(cls, value):
        # This hack is copied from python's standard enum.Enum implementation
        # -------------------------------------------------------------------
        # all SumType instances are actually created during class construction
        # without calling this method; this method is called by the metaclass'
        # __call__ (i.e. Color(3) ), and by pickle
        err_str = f"'{value}' is not a valid {cls.__name__}"
        if type(value) is cls:
            # For lookups like Color(Color.RED)
            return value

        if isinstance(value, cls):
            for variant in cls.__sum_meta__.variants.values():
                if variant is value:
                    return value
            raise ValueError(err_str)
        else:
            try:
                variant_name = cls.__sum_meta__.values[value.lower()]
            except (AttributeError, KeyError):
                raise ValueError(err_str)
            return cls.__sum_meta__.variants[variant_name]

    def __reduce_ex__(self, proto):
        """ Support pickling.
        https://docs.python.org/3.7/library/pickle.html#object.__reduce_ex__
        """
        return self.__class__, (self.__variant_meta__.value, )


def verify_consistency(base_variants, variants):
    if len(base_variants) != len(variants):
        raise TypeError()

    for base_variant, variant in zip(base_variants.values(), variants.values()):
        fst = base_variant.__variant_meta__._asdict()
        snd = variant.__variant_meta__._asdict()
        _ = [(x.pop('constructor'), x.pop('variant_of')) for x in (fst, snd)]
        if fst != snd:
            raise TypeError()


def compare_attrs(attrs, fst, snd):
    return all(getattr(fst, attr) == getattr(snd, attr) for attr in attrs)
