Quickstart Guide
================


.. CAUTION::

    The project is in a beta development status, and a few public
    APIs may change in a backward-incompatible manner.


``typeit`` supports Python 3.6+.


Installation
------------

.. code-block:: bash

    $ pip install typeit


Using CLI tool
--------------

Once installed, ``typeit`` provides you with a CLI tool that allows you to generate a prototype
Python structure of a JSON/YAML data that your app operates with.

For example, try the following snippet in your shell:

.. code-block:: bash

    $ echo '{"first-name": "Hello", "initial": null, "last_name": World}' | typeit gen


You should see output similar to this:

.. code-block:: python

    from typing import NamedTuple, Dict, Any, List, Optional
    from typeit import type_constructor


    class Main(NamedTuple):
        first_name: str
        initial: Optional[Any]
        last_name: str


    overrides = {
        Main.first_name: 'first-name',
    }


    mk_main, dict_main = type_constructor & overrides ^ Main


You can use this snippet as a starting point to improve further.
For instance, you can clarify the ``Optional`` type of the ``Main.initial`` attribute,
and rename the whole structure to better indicate the nature of the data:

.. code-block:: python

    # ... imports ...

    class Person(NamedTuple):
        first_name: str
        initial: Optional[str]
        last_name: str


    overrides = {
        Person.first_name: 'first-name',
    }


    mk_person, dict_person = type_constructor & overrides ^ Person


``typeit`` will handle creation of the constructor ``mk_person :: Dict -> Person`` and the serializer
``dict_person :: Person -> Dict`` for you.

``type_constructor & overrides`` produces a new type constructor that takes overrides into consideration,
and ``type_constructor ^ Person`` reads as "type constructor applied to the Person structure" and essentially
is the same as ``type_constructor(Person)``, but doesn't require parentheses around overrides (and extensions):

.. code-block:: python

    (type_constructor & overrides & extension & ...)(Person)


Overrides
---------

.. CAUTION::

    This functionality may change in a backward-incompatible manner.


As you might have noticed in the example above, ``typeit`` generated a snippet with
a dictionary called ``overrides``, which is passed to the ``type_constructor`` alongside
our ``Person`` type:

.. code-block:: python

    overrides = {
        Person.first_name: 'first-name',
    }


    mk_person, dict_person = type_constructor & overrides ^ Person


This is the way we can indicate that our Python structure has different field
names than the original JSON payload. ``typeit`` code generator created this
dictionary for us because the ``first-name`` attribute of the JSON payload is
not a valid Python variable name (dashes are not allowed in Python variables).

Instead of relying on automatic dasherizing of this attribute (for instance, with a help of
`inflection <https://inflection.readthedocs.io/en/latest/>`_ package), which rarely works
consistently across all possible corner cases, ``typeit`` explicitly
provides you with a reference point in the code, that you can track and refactor with
Intelligent Code Completion tools, should that necessity arise.

You can use the same ``overrides`` object to specify rules for attributes of
any nested types, for instance:

.. code-block:: python

    class Address(NamedTuple):
        street: str
        city: str
        postal_code: str


    class Person(NamedTuple):
        first_name: str
        initial: Optional[str]
        last_name: str
        address: Optional[Address]


    overrides = {
        Person.first_name: 'first-name',
        Address.postal_code: 'postal-code',
    }


    mk_person, dict_person = type_constructor & overrides ^ Person


Supported types by default
--------------------------

* ``bool``
* ``int``
* ``float``
* ``str``
* ``dict``
* ``set`` and ``frozenset``
* ``typing.Any`` passes any value as is
* ``typing.Union`` including nested structures
* ``typing.Sequence``, ``typing.List`` including generic collections with ``typing.TypeVar``.
* ``typing.Set`` and ``typing.FrozenSet``
* ``typing.Tuple``
* ``typing.Dict``
* ``typing.Mapping``
* ``enum.Enum`` derivatives
* ``pathlib.Path`` derivatives
* ``typing_extensions.Literal``
* ``pyrsistent.typing.PVector``
* ``pyrsistent.typing.PMap``


Flags
-----

``NON_STRICT_PRIMITIVES`` -
disables strict checking of primitive types. With this flag, a type constructor for a structure
with a ``x: int`` attribute annotation would allow input values of ``x`` to be strings that could be parsed
as integer numbers. Without this flag, the type constructor will reject those values. The same rule is applicable
to combinations of floats, ints, and bools.

Extensions
----------

TODO

Handling errors
---------------

TODO
