=========
CHANGELOG
=========

3.9.1.5 - 3.9.1.6 (quickfix)
============================

* Support for ``Type[None]``: https://github.com/python/mypy/pull/3754


3.9.1.4
===============

* Minor internal interface changes, no b/w compatibility issues.


3.9.1.3
===============

* Slightly better error reports of Union parsing


3.9.1.2
===============

* Bugfix for unions serialisation of mappings


3.9.1.1
===============

* Support for `typing.NewType`
* Support for forward references and recursive types


3.9.1.0
===============

* Python 3.9 support


0.27.2
===============

* Mapping nested values are serialized according to their custom type definition.


0.27.1
===============

* Experimental tokenizer implementation.


0.26.1
===============

* Support for ``bytes``.


0.25.0
===============

* Mapping types properly deserialize/serialize non-string hashable values.


0.24.0
===============

* Dropped support for Python 3.6;
* Support for classes deriving `Generic[T, U, ...]`;
* Added new type ``typeit.custom_types.JsonString`` - helpful when dealing with JSON strings encoded into JSON strings.


0.23.0
===============

* Support for default values at construction time.


0.22.0
===============

* Support for overrides of init-based types (and dataclasses).


0.21.0
===============

* Support for global attribute name overrides with ``typeit.flags.GlobalNameOverride``
* ``typeit.TypeConstructor`` is now recommended over ``typeit.type_constructor``.
   The latter is left for backward compatibility.
* ``NonStrictPrimitives`` and ``SumTypeDict`` are now recommended over corresponding
  ``NON_STRICT_PRIMITIVES`` ``SUM_TYPE_DICT``. The latter are left for backward compatibility.


0.20.0
===============

* Support Python 3.8

0.19.0
===============

* Generalized attribute name normalization

0.18.0
===============

* SumType variants are attribute-strict #48

0.16.0 - 0.17.0
===============

* Combinator for flags and extensions #45
* Change interface for Flags and Extensions

0.15.0
==============

* SumType from/to mapping #43
* Support explicit tags for SumType Variants #32
* Parser memoization #38

0.14.1
==============

* Fix root object validation error handling

0.14.0
==============

* Support builtins parsing #24
* Codegen for Sequence root objects #37
* [api breaking change] simpler error handling interface

0.13.0
==============

* Added support for regular classes with annotated ``__init__``.

0.12.1, 0.12.2
==============

* Experimental support for SumType.

0.12.0
============

* ``typeit.iter_invalid`` replaces ``typeit.utils.iter_invalid_data``.
* Add support for ``pyrsistent.typing.PVector`` and ``pyrsistent.typing.PMap`` types.
* Add support for ``Literals``.

0.11.0
============

* ``pyrsistent`` is now part of minimal dependencies.
* Add support for chaining / compositional API for overrides.

0.10.1
============

* Fix bug in serialization of union types.

0.10.0
============

* Fix bug in parsing union types with sequence variants.
* Primitive types switched to strict matching.
* Non-strict primitives flag `NonStrictPrimitives` is available for overrides.
* Added support for `typing.Mapping`
* Added support for `pathlib.Path`

0.9.0
============

* Dependencies were split into minimal / extras.

0.8.1
============

* `utils.iter_invalid_data()` does not throws KeyError when sample value is missing.

0.8.0
============

* Added a utility function for iterating over invalid data samples.

0.7.3
============

* Internal dependencies updated.

0.7.1, 0.7.2
============

* Fixed bug in Union serialization.

0.7.0
=====

* Added support for overrides;
* Added support for fixed-length Tuples;
* Added support for Sets.
