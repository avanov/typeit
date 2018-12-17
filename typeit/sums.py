import logging
import re
from typing import Dict, Any, get_type_hints, Type, Iterator, Set, Generic, TypeVar
from typing_extensions import Protocol
import typing_inspect as t_insp


# Internal type variable used for Type[].
SVT = TypeVar('SVT', covariant=True, bound=type)


class Variant(Protocol, Generic[SVT]):
    data: SVT

    def __call__(self, *args, **kwargs) -> SVT:
        ...


log = logging.getLogger(__name__)


SUM_TYPE_VARIANT_NAME_RE = re.compile('^[A-Z][0-9A-Z_]*$')


class SumTypeMetaData:
    __slots__ = ('type', 'variants', 'values', 'matches')

    def __init__(self,
                 type,
                 variants: Dict[str, 'SumType'],
                 values: Dict[str, str],
                 matches: Dict[str, Dict[Any, Any]]) -> None:
        self.type = type
        self.variants = variants
        self.values = values
        self.matches = matches


# This hack is copied from python's standard enum.Enum implementation:
# ------------
# Dummy value for SumType as SumTypeMetaclass explicitly checks for it,
# but of course until SumTypeMetaclass finishes running the first time
# the SumType class doesn't exist.
# This is also why there are checks in SumTypeMetaclass like
# `if SumType is not None`
SumType = None


class SumTypeMetaclass(type):
    """ Metaclass object to be used with the actual SumType implementation.
    """
    def __new__(mcs, class_name: str, bases, attrs: Dict[str, Any]):
        """ This magic method is called when a new SumType class is being defined and parsed.
        """
        sum_cls = type.__new__(mcs, class_name, bases, attrs)

        variants = {}
        variant_values = {}
        variant_constructors = get_type_hints(sum_cls)

        # 1. Populating variants from long-form definitions:
        #    class A(SumType):
        #        B[: type] = value
        # --------------------------------------------------
        for attr_name, value in attrs.items():
            # Populating variants from long-form definitions:
            # class A(SumType):
            #     B[: type] = value
            if not SUM_TYPE_VARIANT_NAME_RE.match(attr_name):
                continue

            if attr_name not in variant_constructors:
                raise TypeError(f'SumType Variant "{sum_cls.__module__}::{sum_cls.__name__}::{attr_name}" '
                                'must have a value constructor. '
                                'You need to specify it as a type hint. Example:\n'
                                'class X(SumType):\n'
                                "    X: str = 'x'\n")

            print(variant_constructors[attr_name])
            constructor = t_insp.get_args(
                variant_constructors[attr_name]
            )[0]
            variant = object.__new__(sum_cls)
            variant.__init__(
                variant_of=sum_cls,
                name=attr_name,
                constructor=constructor,
                value=value
            )

            setattr(sum_cls, attr_name, variant)
            variants[attr_name] = variant
            variant_values[value] = attr_name

        # 2. Populating variants from short-form definitions:
        #    class A(SumType):
        #        B: type
        # --------------------------------------------------
        # note that the value will be a lower-case version of the variant name
        for attr_name, constructor in variant_constructors.items():
            if not SUM_TYPE_VARIANT_NAME_RE.match(attr_name):
                continue
            if attr_name in variants:
                continue

            constructor = t_insp.get_args(constructor)[0]
            value = attr_name.lower()
            variant = object.__new__(sum_cls)
            variant.__init__(
                variant_of=sum_cls,
                name=attr_name,
                constructor=constructor,
                value=value
            )

            setattr(sum_cls, attr_name, variant)
            variants[attr_name] = variant
            variant_values[value] = attr_name

        # 4. Finalize
        # --------------------------------------------------
        sum_cls.__sum_meta__ = SumTypeMetaData(
            type=sum_cls,
            # set of SumType variants
            variants=variants,
            # dict of value => variant mappings
            values=variant_values,
            # dict of value => match instances.
            # Used by .match() for O(1) result retrieval
            matches={v: {} for v in variants}
        )

        # 5. Hacks to mimic Enum interface
        # --------------------------------------------------
        # 5.1 This hack is copied from python's standard enum.Enum implementation:
        # replace any other __new__ with our own (as long as SumType is not None,
        # anyway) -- again, this is to support pickle
        if SumType is not None:
            sum_cls.__new__ = SumType.__new__
        return sum_cls

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

    class Mismatch(Exception):
        pass

    class PatternError(Exception):
        pass

    @classmethod
    def values(cls) -> Set:
        return set(cls.__sum_meta__.values.keys())

    @classmethod
    def match(cls, value) -> 'SumType':
        """
        :rtype: dict or :class:`types.FunctionType`
        """
        variant = None
        for variant_name, variant_type in cls.__sum_meta__.variants.items():
            if variant_type.is_primitive_type():
                # We compare primitive types with equality matching
                if value == variant_type.value:
                    variant = variant_type
                    break
            else:
                # We compare non-primitive types with type checking
                if isinstance(value, variant_type.value):
                    variant = variant_type
                    break

        if variant is None:
            raise cls.Mismatch(
                'Variant value "{value}" is not a part of the type {type}: {values}'.format(
                    value=value,
                    type=cls.__sum_meta__.type,
                    values=u', '.join(['{val} => {var}'.format(val=val, var=var)
                                       for val, var in cls.__sum_meta__.values.items()])
                )
            )

        return variant

    @classmethod
    def inline_match(cls, **inline_cases):
        all_cases = set(cls.__sum_meta__.variants.keys())
        inline_cases = inline_cases.items()
        checked_cases = []
        for variant_name, fun in inline_cases:
            try:
                variant = cls.__sum_meta__.variants[variant_name]
            except KeyError:
                raise cls.PatternError(
                    'Variant {variant} does not belong to the type {type}'.format(
                        variant=str(variant_name),
                        type=cls.__sum_meta__.type,
                    )
                )
            all_cases.remove(variant.name)
            checked_cases.append((variant, fun))

        if all_cases:
            raise cls.PatternError(
                'Inline cases are not exhaustive.\n'
                'Here is the variant that is not matched: {variant} '.format(
                    variant=list(all_cases)[0]
                )
            )

        def matcher(value):
            for variant, fun in checked_cases:
                if variant.is_primitive_type():
                    if value == variant.value:
                        return fun
                else:
                    if isinstance(value, variant.value):
                        return fun

            raise cls.Mismatch(
                'Variant value "{value}" is not a part of the type {type}: {values}'.format(
                    value=value,
                    type=cls.__sum_meta__.type,
                    values=u', '.join(['{val} => {var}'.format(val=val, var=var)
                                       for val, var in cls.__sum_meta__.values.items()])
                )
            )
        return matcher

    def __init__(self,
                 variant_of: Type['SumType'],
                 name: str,
                 constructor,
                 value,
                 data_args=None,
                 data_kwargs=None) -> None:
        """
        :param variant_of: class of the SumType this variant instance belongs to
        :param name: name of the variant, as it is defined in the source code (uppercase)
        :param value: variant value
        :param constructor: constructor for a data that this variant can hold
        """
        self.variant_of = variant_of
        self.name = name
        self.value = value
        self.constructor = constructor
        if data_args or data_kwargs:
            self.data = constructor(*data_args, **data_kwargs)

    def is_primitive_type(self) -> bool:
        return self.constructor in (int, str, float, bool)

    def __call__(self, *data_args, **data_kwargs) -> 'SumType':
        """ Returns a data-holding variant"""
        instance = object.__new__(self.__class__)
        instance.__init__(
            variant_of=self.variant_of,
            name=self.name,
            constructor=self.constructor,
            value=self.value,
            data_args=data_args,
            data_kwargs=data_kwargs,
        )
        return instance

    def __eq__(self, other: 'SumType') -> bool:
        """ This method is redefined only to simplify variant comparison for tests with mocks that
        might do things like mocked_function.assert_called_with(SumType.VARIANT)
        """
        return all([
            self.variant_of is other.variant_of,
            self.name == other.name,
            self.value == other.value,
            self.constructor == other.constructor
        ])

    # https://docs.python.org/3/reference/datamodel.html#object.__hash__
    # If a class that overrides __eq__() needs to retain the implementation of __hash__() from a parent class,
    # the interpreter must be told this explicitly by setting __hash__ = <ParentClass>.__hash__
    __hash__ = object.__hash__

    def __repr__(self) -> str:
        return (
            f'SumType(type={self.variant_of.__module__}.{self.variant_of.__name__}, '
            f'name={self.name}, value={self.value})'
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
                variant_name = cls.__sum_meta__.values[value]
            except KeyError:
                raise ValueError(err_str)
            return cls.__sum_meta__.variants[variant_name]

    def __reduce_ex__(self, proto):
        """ Support pickling.
        https://docs.python.org/3.7/library/pickle.html#object.__reduce_ex__
        """
        return self.__class__, (self.value, )
