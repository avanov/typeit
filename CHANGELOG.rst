=========
CHANGELOG
=========

0.10.1
============

* Fix bug in serialization of union types.

0.10.0
============

* Fix bug in parsing union types with sequence variants.
* Primitive types switched to strict matching.
* Non-strict primitives flag `NON_STRICT_PRIMITIVES` is available for overrides.
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
