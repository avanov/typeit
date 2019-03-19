Quickstart Guide
================


.. CAUTION::

    The project is in an early development status, and a few public
    APIs may change in a backward-incompatible manner.


``typeit`` supports Python 3.7+.


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


    mk_main, dict_main = type_constructor(Main, overrides)


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


    mk_person, dict_person = type_constructor(Person, overrides)


``typeit`` will handle creation of the constructor ``mk_person :: Dict -> Person`` and the serializer
``dict_person :: Person -> Dict`` for you.


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


    mk_person, dict_person = type_constructor(Person, overrides)


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


    mk_person, dict_person = type_constructor(Person, overrides)

